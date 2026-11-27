######################################################################
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
######################################################################
"""
Product API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
  codecov --token=$CODECOV_TOKEN

  While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_service.py:TestProductService
"""
import os
import logging
from decimal import Decimal
from unittest import TestCase
from service import app
from service.common import status
from service.models import db, init_db, Product
from tests.factories import ProductFactory

# Disable all but critical errors during normal test run
# uncomment for debugging failing tests
# logging.disable(logging.CRITICAL)

# DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///../db/test.db')
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)
BASE_URL = "/products"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductRoutes(TestCase):
    """Product Service tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        db.session.remove()

    ############################################################
    # Utility function to bulk create products
    ############################################################
    def _create_products(self, count: int = 1) -> list:
        """Factory method to create products in bulk"""
        products = []
        for _ in range(count):
            test_product = ProductFactory()
            response = self.client.post(BASE_URL, json=test_product.serialize())
            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, "Could not create test product"
            )
            new_product = response.get_json()
            test_product.id = new_product["id"]
            products.append(test_product)
        return products

    ############################################################
    #  T E S T   C A S E S
    ############################################################
    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"Product Catalog Administration", response.data)

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data['message'], 'OK')

    # ----------------------------------------------------------
    # TEST CREATE
    # ----------------------------------------------------------
    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()
        logging.debug("Test Product: %s", test_product.serialize())
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

        #
        # Uncomment this code once READ is implemented
        #

        # # Check that the location header was correct
        response = self.client.get(f"{BASE_URL}/{new_product['id']}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

    def test_create_product_with_no_name(self):
        """It should not Create a Product without a name"""
        product = self._create_products()[0]
        new_product = product.serialize()
        del new_product["name"]
        logging.debug("Product no name: %s", new_product)
        response = self.client.post(BASE_URL, json=new_product)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_no_content_type(self):
        """It should not Create a Product with no Content-Type"""
        response = self.client.post(BASE_URL, data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_wrong_content_type(self):
        """It should not Create a Product with wrong Content-Type"""
        response = self.client.post(BASE_URL, data={}, content_type="plain/text")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    #
    # ADD YOUR TEST CASES HERE
    #

    ######################################################################
    # Utility functions
    ######################################################################

    def get_product_count(self):
        """save the current number of products"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        # logging.debug("data = %s", data)
        return len(data)

    def test_read_product(self):
        """It should return a product from database"""

        product = ProductFactory.build()
        response = self.client.post(BASE_URL, json=product.serialize())
        self.assertEqual(201, response.status_code)
        id = response.json['id']

        response = self.client.get(f'{BASE_URL}/{id}')
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
        response = self.client.post(BASE_URL, json=product.serialize())
        self.assertEqual(201, response.status_code)
        id = response.json['id']

        updated_product = ProductFactory.build()
        updated_product.id = id
        response = self.client.put(f'{BASE_URL}/{id}', json=updated_product.serialize())
        self.assertEqual(200, response.status_code)

        response = self.client.get(f'{BASE_URL}')
        self.assertEqual(200, response.status_code)

        product = Product()
        product.deserialize(response.json[0])
        self.assertEqual(updated_product.name, product.name)
        self.assertEqual(updated_product.description, product.description)
        self.assertEqual(Decimal(updated_product.price), product.price)
        self.assertEqual(updated_product.available, product.available)
        self.assertEqual(updated_product.category, product.category)

    def test_delete_product(self):
        """It should delete a product from database"""

        product = ProductFactory.build()
        response = self.client.post(BASE_URL, json=product.serialize())
        self.assertEqual(201, response.status_code)
        product.id = response.json['id']

        response = self.client.delete(f'{BASE_URL}/{product.id}')
        self.assertEqual(204, response.status_code)

        response = self.client.get(f'{BASE_URL}')
        self.assertEqual(200, response.status_code)
        self.assertEqual([], response.json)

    def test_list_products(self):
        """It should list all products from database"""

        products = []
        for _ in range(5):
            product = ProductFactory.build()
            response = self.client.post(BASE_URL, json=product.serialize())
            self.assertEqual(201, response.status_code)
            product.id = response.json['id']
            products.append(product)

        response = self.client.get(f'{BASE_URL}')
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
        for _ in range(5):
            product = ProductFactory.build()
            response = self.client.post(BASE_URL, json=product.serialize())
            self.assertEqual(201, response.status_code)
            product.id = response.json['id']
            products.append(product)
            if product.name not in by_name:
                by_name[product.name] = [product]
            else:
                by_name[product.name].append(product)

        name = products[0].name
        response = self.client.get(f'{BASE_URL}', query_string={
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
        for _ in range(5):
            product = ProductFactory.build()
            response = self.client.post(BASE_URL, json=product.serialize())
            self.assertEqual(201, response.status_code)
            product.id = response.json['id']
            products.append(product)
            if product.available not in by_availability:
                by_availability[product.available] = [product]
            else:
                by_availability[product.available].append(product)

        available = products[0].available
        response = self.client.get(f'{BASE_URL}', query_string={
            'available': available,
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
        for _ in range(5):
            product = ProductFactory.build()
            response = self.client.post(BASE_URL, json=product.serialize())
            self.assertEqual(201, response.status_code)
            product.id = response.json['id']
            products.append(product)
            if product.category not in by_category:
                by_category[product.category] = [product]
            else:
                by_category[product.category].append(product)

        category = products[0].category
        response = app.test_client().get(f'{BASE_URL}', query_string={
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
        for _ in range(5):
            product = ProductFactory.build()
            response = self.client.post(BASE_URL, json=product.serialize())
            self.assertEqual(201, response.status_code)
            product.id = response.json['id']
            products.append(product)
            if product.price not in by_price:
                by_price[product.price] = [product]
            else:
                by_price[product.price].append(product)

        price = products[0].price
        response = app.test_client().get('/products', query_string={
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
