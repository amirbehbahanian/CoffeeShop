from enum import Enum
from datetime import datetime
import csv
from scipy import stats
import numpy as np
import random
import logging

class Drink:
    def __init__(self, name, mean, std):
        self.mu = mean
        self.std = std
        self.name = name

class Skill(Enum):
    Amature = 1
    midlevel = 2
    expert = 3

class Barista:
    def __init__(self, csv_file, level):
        """
        The order of the lines in __init__ matters
        """
        self.level = level
        self.drink_list = []
        self._read_csv(csv_file)
        self.customer = None
    
    def _read_csv(self, csv_file):
        with open(csv_file, 'r') as file:
            reader = csv.reader(file)
            next(reader)  
            for row in reader:
                drink_name = row[0].strip().lower() 
                match self.level:
                    case Skill.Amature:
                        mean = float(row[1]) + 0.2 * float(row[1])
                        std = float(row[2]) + 0.2 * float(row[2])
                    case Skill.midlevel:
                        mean = float(row[1])
                        std = float(row[2])
                    case Skill.expert:
                        mean = float(row[1]) - 0.2 * float(row[1])
                        std = float(row[2]) - 0.2 * float(row[2])
                drink = Drink(drink_name, mean, std)
                setattr(self, drink_name, drink)
                self.__dict__[drink_name] = drink
                self.drink_list.append(drink_name)

class Status(Enum):
    in_row = 1
    ordering = 2
    waiting_for_drink = 3

class Character(Enum):
    IMPULSIVE_IRENE = (10, "Enthusiastic but sometimes a little short-tempered. Generally polite, but their impulsiveness can make them seem impatient.")
    SPEEDY_SAM = (20, "Typically calm and polite but focused on efficiency. Doesn't like to waste time, but remains courteous.")
    DELIBERATE_DAN = (30, "Patient and polite, but can be perceived as a bit indecisive. Likely to ask detailed questions before making a decision.")
    CASUAL_CARL = (45, "Laid-back and easygoing, with a polite and friendly demeanor. Not in a hurry, so rarely shows any signs of frustration.")

class Customer:
    def __init__(self, position_in_row:int, character:Character, arrival_time:datetime) -> None:
        self.position_in_row = position_in_row
        self.arrival_time:datetime = arrival_time
        self.status = Status.in_row
        self.character = character
        self.order_start_time:datetime = None
        self.order_time:datetime = None
        self.next = None
        self.order:Drink = None
        
    def is_drink_ready(self, current_time:datetime):
        time_waited = current_time - self.order_time
        p = stats.norm.cdf(int(time_waited.total_seconds() / 60), loc=self.order.mu, scale=self.order.std)
        k = np.random.choice([0,1],p = [1-p,p])
        return k
    
class Waitingline:
    def __init__(self) -> None:
        self.last = None

    def __repr__(self) -> str:
        node = self.last
        nodes = []
        while node is not None:
            nodes.append(f"Position: {node.position_in_row} - Arrival: {node.arrival_time}")
            node = node.next
        nodes.append("reached the counter")
        return " -> ".join(nodes)
    
    def __iter__(self):
        node = self.last
        while node is not None:
            yield node
            node = node.next
    
    def count_customers(self):
        count = 1
        node = self.last
        while node.next is not None:
            count+=1
            node = node.next
        return count

    def quit_line(self):
        node = self.last
        while node.next is not None:
            node_prev = node
            node = node.next
        node_prev.next = None
        return node
    
    def enter_line(self, new_node:Customer):
        if self.last is None:
            self.last = new_node
        else:
            node = self.last
            new_node.next = node
            self.last = new_node

class Rushhour:
    def __init__(self, order_list:Waitingline) -> None:
        self.order_list = order_list
        self.barista_list = []
        self.drink_wait_list = []

    def add_barista(self, barista:Barista):
        self.barista_list.append(barista)

    def find_barista_and_order(self, time:datetime):
        for b in self.barista_list:
            if b.customer is None:
                b.customer = self.order_list.quit_line()
                b.customer.order_start_time = time
                b.customer.status = Status.ordering
            else:
                waited_time = time - b.customer.order_start_time
                if waited_time.total_seconds() >= b.customer.character.value[0]:
                    b.customer.status = Status.waiting_for_drink
                    b.customer.order_time = time
                    b.customer.order = b.__dict__[random.choice(b.drink_list)]
                    self.drink_wait_list.append(b.customer)
                    b.customer = None

    def serve_drink_wait_list(self, time, logger):
        for c in self.drink_wait_list[-1:]:
            k = c.is_drink_ready(time)
            if k==1:
                self.drink_wait_list.pop()
                logger.info(f"Arrival: {c.arrival_time} | In front of barista: {c.order_start_time} | Ordering time: {c.order_time} | Order: {c.order.name} | Time to ready: {time - c.order_time}")
                
if __name__=="__main__":
    default_time = datetime(2024, 9, 14)
    waiting_line = Waitingline()
    for i in range(1,4):
        globals()[f"customer{i}"] = Customer(
            position_in_row = i, 
            character=Character.CASUAL_CARL, 
            arrival_time = default_time)
        waiting_line.enter_line(globals()[f"customer{i}"])
    print(waiting_line)