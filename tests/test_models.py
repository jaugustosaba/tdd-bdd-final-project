# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Test cases for Product Model

Test cases can be run with:
    nosetests
    coverage report -m

While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_models.py:TestProductModel

"""
import os
import logging
import unittest
from decimal import Decimal
from service.models import Product, Category, db, DataValidationError
from service import app
from tests.factories import ProductFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)


######################################################################
#  P R O D U C T   M O D E L   T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductModel(unittest.TestCase):
    """Test Cases for Product Model"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        Product.init_db(app)

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_healthcheck(self):
        """It should return ok on healthcheck"""
        response = app.test_client().get('/health')
        self.assertEqual(200, response.status_code)
        data = response.json
        self.assertEqual(data['message'], 'OK')

    def test_update_no_id(self):
        """It should return error when updating with no id"""
        product = Product()
        self.assertRaises(DataValidationError, product.update)

    def test_create_a_product(self):
        """It should Create a product and assert that it exists"""
        product = Product(name="Fedora", description="A red hat", price=12.50, available=True, category=Category.CLOTHS)
        self.assertEqual(str(product), "<Product Fedora id=[None]>")
        self.assertTrue(product is not None)
        self.assertEqual(product.id, None)
        self.assertEqual(product.name, "Fedora")
        self.assertEqual(product.description, "A red hat")
        self.assertEqual(product.available, True)
        self.assertEqual(product.price, 12.50)
        self.assertEqual(product.category, Category.CLOTHS)

    def test_add_a_product(self):
        """It should Create a product and add it to the database"""
        products = Product.all()
        self.assertEqual(products, [])
        product = ProductFactory()
        product.id = None
        product.create()
        # Assert that it was assigned an id and shows up in the database
        self.assertIsNotNone(product.id)
        products = Product.all()
        self.assertEqual(len(products), 1)
        # Check that it matches the original product
        new_product = products[0]
        self.assertEqual(new_product.name, product.name)
        self.assertEqual(new_product.description, product.description)
        self.assertEqual(Decimal(new_product.price), product.price)
        self.assertEqual(new_product.available, product.available)
        self.assertEqual(new_product.category, product.category)
    
    def test_product_deserialize_invalid_type(self):
        """It should return an error if an attribute is missing"""
        data = "a string"
        new = Product()
        self.assertRaises(DataValidationError, new.deserialize, data)

    def test_product_deserialize_missing_attribute(self):
        """It should return an error if an attribute is missing"""
        product = ProductFactory.build()
        data = product.serialize()
        del data['name']
        new = Product()
        self.assertRaises(DataValidationError, new.deserialize, data)

    def test_product_deserialize_availability_not_bool(self):
        """It should return an error if an availability is not bool"""
        product = ProductFactory.build()
        data = product.serialize()
        data['available'] = 1
        new = Product()
        self.assertRaises(DataValidationError, new.deserialize, data)

    def test_product_deserialize_invalid_category(self):
        """It should return an error if category is invalid"""
        product = ProductFactory.build()
        data = product.serialize()
        data['category'] = 'DUMMY'
        new = Product()
        self.assertRaises(DataValidationError, new.deserialize, data)

    def test_find_price_using_string(self):
        """It should accept find products by price using strings"""
        products = Product.find_by_price('1.0')
        self.assertIsNotNone(products)

    def test_missing_content_type(self):
        """It should return an error for invalid content types"""
        response = app.test_client().post(f'/products')
        self.assertEqual(response.status_code, 415)

    def test_add_invalid_content_type(self):
        """It should return an error for invalid content types"""
        response = app.test_client().post(f'/products', 
            headers={'Content-Type': 'text/html'})
        self.assertEqual(response.status_code, 415)

    def test_create_product(self):
        """It should create a product"""

        product = ProductFactory.build()
        response = app.test_client().post('/products', json=product.serialize())
        self.assertEqual(201, response.status_code)
        products = Product.all()
        self.assertEqual(1, len(products))
        created_product = products[0]
        self.assertEqual(created_product.name, product.name)
        self.assertEqual(created_product.description, product.description)
        self.assertEqual(Decimal(created_product.price), product.price)
        self.assertEqual(created_product.available, product.available)
        self.assertEqual(created_product.category, product.category)

    def test_read_product(self):
        """It should return a product from database"""

        product = ProductFactory.build()
        product.create()
        self.assertIsNotNone(product.id)

        response = app.test_client().get(f'/products/{product.id}')
        self.assertEqual(200, response.status_code)
        returned_product = response.json
        self.assertEqual(returned_product['name'], product.name)
        self.assertEqual(returned_product['description'], product.description)
        self.assertEqual(Decimal(returned_product['price']), product.price)
        self.assertEqual(returned_product['available'], product.available)
        self.assertEqual(returned_product['category'], product.category.name)

    def test_update_product(self):
        """It should update a product from database"""

        product = ProductFactory.build()
        product.create()
        self.assertIsNotNone(product.id)

        updated_product = ProductFactory.build()
        updated_product.id = None
        response = app.test_client().put(f'/products/{product.id}', json=updated_product.serialize())
        self.assertEqual(200, response.status_code)

        product = Product.find(product.id)
        self.assertEqual(updated_product.name, product.name)
        self.assertEqual(updated_product.description, product.description)
        self.assertEqual(Decimal(updated_product.price), product.price)
        self.assertEqual(updated_product.available, product.available)
        self.assertEqual(updated_product.category, product.category)

    def test_delete_product(self):
        """It should delete a product from database"""

        product = ProductFactory.build()
        product.create()
        self.assertIsNotNone(product.id)

        response = app.test_client().delete(f'/products/{product.id}')
        self.assertEqual(204, response.status_code)
        self.assertIsNone(Product.find(product.id))

    def test_list_products(self):
        """It should list all products from database"""

        products = []
        for i in range(5):
            product = ProductFactory.build()
            product.create()
            products.append(product)

        response = app.test_client().get(f'/products')
        self.assertEqual(200, response.status_code)
        self.assertEqual(5, len(response.json))

        for expected_product, product in zip(products, response.json):
            self.assertEqual(product['name'], expected_product.name)
            self.assertEqual(product['description'], expected_product.description)
            self.assertEqual(Decimal(product['price']), expected_product.price)
            self.assertEqual(product['available'], expected_product.available)
            self.assertEqual(product['category'], expected_product.category.name)

    def test_list_products_by_name(self):
        """It should list all products from database by name"""

        products = []
        by_name = {}
        for i in range(5):
            product = ProductFactory.build()
            product.create()
            products.append(product)
            if product.name not in by_name:
                by_name[product.name] = [product]
            else:
                by_name[product.name].append(product)

        name = products[0].name
        response = app.test_client().get(f'/products', query_string={
            'name': name,
        })
        self.assertEqual(200, response.status_code)
        self.assertEqual(len(by_name[name]), len(response.json))

        for expected_product, product in zip(by_name[name], response.json):
            self.assertEqual(product['name'], expected_product.name)
            self.assertEqual(product['description'], expected_product.description)
            self.assertEqual(Decimal(product['price']), expected_product.price)
            self.assertEqual(product['available'], expected_product.available)
            self.assertEqual(product['category'], expected_product.category.name)


    def test_list_products_by_availability(self):
        """It should list all products from database by availability"""

        products = []
        by_availability = {}
        for i in range(5):
            product = ProductFactory.build()
            product.create()
            products.append(product)
            if product.available not in by_availability:
                by_availability[product.available] = [product]
            else:
                by_availability[product.available].append(product)

        available = products[0].available
        response = app.test_client().get(f'/products', query_string={
            'availability': available,
        })
        self.assertEqual(200, response.status_code)
        self.assertEqual(len(by_availability[available]), len(response.json))

        for expected_product, product in zip(by_availability[available], response.json):
            self.assertEqual(product['name'], expected_product.name)
            self.assertEqual(product['description'], expected_product.description)
            self.assertEqual(Decimal(product['price']), expected_product.price)
            self.assertEqual(product['available'], expected_product.available)
            self.assertEqual(product['category'], expected_product.category.name)

    def test_list_products_by_category(self):
        """It should list all products from database by availability"""

        products = []
        by_category = {}
        for i in range(5):
            product = ProductFactory.build()
            product.create()
            products.append(product)
            if product.category not in by_category:
                by_category[product.category] = [product]
            else:
                by_category[product.category].append(product)

        category = products[0].category
        response = app.test_client().get(f'/products', query_string={
            'category': category.name,
        })
        self.assertEqual(200, response.status_code)
        self.assertEqual(len(by_category[category]), len(response.json))

        for expected_product, product in zip(by_category[category], response.json):
            self.assertEqual(product['name'], expected_product.name)
            self.assertEqual(product['description'], expected_product.description)
            self.assertEqual(Decimal(product['price']), expected_product.price)
            self.assertEqual(product['available'], expected_product.available)
            self.assertEqual(product['category'], expected_product.category.name)

    def test_list_products_by_price(self):
        """It should list all products from database by price"""

        products = []
        by_price = {}
        for i in range(5):
            product = ProductFactory.build()
            product.create()
            products.append(product)
            if product.price not in by_price:
                by_price[product.price] = [product]
            else:
                by_price[product.price].append(product)

        price = products[0].price
        response = app.test_client().get(f'/products', query_string={
            'price': price,
        })
        self.assertEqual(200, response.status_code)
        self.assertEqual(len(by_price[price]), len(response.json))

        for expected_product, product in zip(by_price[price], response.json):
            self.assertEqual(product['name'], expected_product.name)
            self.assertEqual(product['description'], expected_product.description)
            self.assertEqual(Decimal(product['price']), expected_product.price)
            self.assertEqual(product['available'], expected_product.available)
            self.assertEqual(product['category'], expected_product.category.name)