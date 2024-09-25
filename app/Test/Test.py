from BE_Coffee_Shop import Customer, Barista, Skill, Status, Character,Waitingline, Rushhour, Drink, Simulation, RabbitMQProducer
import unittest
import logging
from dependency_injector import containers, providers
from datetime import datetime
import os
import pika
import json
from unittest.mock import patch, MagicMock


csv_path = os.path.join(os.getcwd() ,"Test", "test.csv")

class Container(containers.DeclarativeContainer):
    barista_factory = providers.Factory(
        Barista, 
        csv_file=providers.Dependency(),
        level=providers.Dependency()
    )
    
    customer_factory = providers.Factory(
        Customer,
        position_in_row = providers.Dependency(),
        arrival_time = providers.Dependency()
    )

    waiting_line_factory = providers.Factory(
        Waitingline
    )

    rush_hour_factory = providers.Factory(
        Rushhour,
        order_list = providers.Dependency()
    )

class testBE(unittest.TestCase):
    def setUp(self):
        self.container = Container()
        self.default_time = datetime(2024, 9, 14)

    def test_barista(self):
        barista = self.container.barista_factory(csv_file = csv_path, level=Skill.midlevel)
        self.assertEqual(barista.level.value, 2)
        self.assertEqual(barista.latte.mu, 5)
        self.assertEqual(barista.latte.std, 1)

    def test_customer(self):
        barista = self.container.barista_factory(csv_file = csv_path, level=Skill.midlevel)
        customer = self.container.customer_factory(position_in_row = 1, character=Character.CASUAL_CARL, arrival_time = self.default_time)
        customer.order = barista.latte
        self.assertEqual(customer.position_in_row, 1)
        self.assertEqual(customer.arrival_time, self.default_time)
        self.assertEqual(customer.next, None)
        self.assertEqual(customer.order_time, None)
        self.assertEqual(customer.status, Status.in_row)
        self.assertEqual(customer.character, Character.CASUAL_CARL)
        self.assertEqual(customer.order.mu, 5)
        self.assertEqual(customer.order.std, 1)

    def test_order_line(self):
        waiting_line = self.container.waiting_line_factory()
        for i in range(1,4):
            globals()[f"customer{i}"] = self.container.customer_factory(
                position_in_row = i, 
                character=Character.CASUAL_CARL, 
                arrival_time = self.default_time)
            waiting_line.enter_line(globals()[f"customer{i}"])
        self.assertEqual(waiting_line.count_customers(), 3)
        _ = waiting_line.quit_line()
        self.assertEqual(waiting_line.count_customers(), 2)
        customer = self.container.customer_factory(
                                                    position_in_row = i, 
                                                    character=Character.CASUAL_CARL, 
                                                    arrival_time = self.default_time
                                                    )
        waiting_line.enter_line(customer)
        self.assertEqual(waiting_line.count_customers(), 3)

    def test_rush_hour(self):
        barista = self.container.barista_factory(csv_file = csv_path, level=Skill.midlevel)
        waiting_line = self.container.waiting_line_factory()
        for i in range(1,4):
            globals()[f"customer{i}"] = self.container.customer_factory(
                position_in_row = i, 
                character=Character.CASUAL_CARL, 
                arrival_time = self.default_time)
            waiting_line.enter_line(globals()[f"customer{i}"])  
        rush_hour = self.container.rush_hour_factory(order_list = waiting_line)
        rush_hour.add_barista(barista=barista)
        self.assertEqual(rush_hour.barista_list[0].level, Skill.midlevel)   

        rush_hour.find_barista_and_order(time=datetime(2024, 10, 10, 12, 10))
        self.assertEqual(waiting_line.count_customers(), 2)
        self.assertEqual(rush_hour.barista_list[0].customer.order_start_time, datetime(2024, 10, 10, 12, 10))
        self.assertEqual(rush_hour.barista_list[0].customer.status, Status.ordering)
        rush_hour.find_barista_and_order(time=datetime(2024, 10, 10, 12, 10, 50))
        self.assertEqual(rush_hour.drink_wait_list[0].status, Status.waiting_for_drink)
        self.assertEqual(rush_hour.drink_wait_list[0].order_time, datetime(2024, 10, 10, 12, 10, 50))
        self.assertIsInstance(rush_hour.drink_wait_list[0].order, Drink)
        save_path = os.path.join(os.getcwd(), 'my_logger.out')
        if os.path.exists(save_path):
            os.remove(save_path)
        logger = logging.getLogger('CoffeeShopLogger')
        logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler(save_path)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        rush_hour.serve_drink_wait_list(time=datetime(2024, 10, 10, 12, 25, 50), logger=logger)
        self.assertTrue(os.path.exists(save_path))

    @patch("pika.BlockingConnection")
    def test_rabitmq_send(self, mock_blocking_connection):
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_blocking_connection.return_value = mock_connection
        mock_connection.channel.return_value = mock_channel

        producer = RabbitMQProducer(queue_name='test_queue')
        message_dict = {"barista": 2, "customer": 5}
        producer.send_message(message_dict)

        mock_blocking_connection.assert_called_once_with(pika.ConnectionParameters('localhost'))
        mock_connection.channel.assert_called_once()
        mock_channel.queue_declare.assert_called_once_with(queue='test_queue', durable=True)
        mock_channel.basic_publish.assert_called_once_with(
            exchange='',
            routing_key='test_queue',
            body=json.dumps(message_dict),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        mock_connection.close.assert_called_once()

    @patch('pika.BlockingConnection')
    def test_start_consuming(self, mock_blocking_connection):
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_blocking_connection.return_value = mock_connection
        mock_connection.channel.return_value = mock_channel

        mock_method_frame = MagicMock()
        mock_method_frame.delivery_tag = 'tag'
        mock_channel.basic_get.return_value = (mock_method_frame, None, json.dumps({"barista": 2, "customer": 5}).encode())

        simulation = Simulation(menu_path='test.csv')
        
        with patch('builtins.print') as mocked_print:
            simulation.start_consuming(max_iterations=1)  # Limit iterations to 1 to prevent infinite loop

        mock_blocking_connection.assert_called_once_with(pika.ConnectionParameters('localhost'))
        mock_connection.channel.assert_called_once()
        mock_channel.queue_declare.assert_called_once_with(queue='run_simulation', durable=True)
        mock_channel.basic_get.assert_called_with(queue='run_simulation', auto_ack=True)
        mocked_print.assert_called_with({"barista": 2, "customer": 5})

if __name__=="__main__":
    unittest.main()