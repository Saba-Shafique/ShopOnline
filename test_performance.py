import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from main import app
from models import User
from pydantic import BaseModel

client = TestClient(app)


# sample data
user_data = {
    "email": "test@example.com",
    "password": "password123",
    "confirm_password": "password123"
}

# user Signup:
@pytest.mark.benchmark(group="users")
def test_signup_performance(benchmark):
    response = benchmark(client.post, "/users/signup/", json=user_data)
    assert response.status_code == 200 or response.status_code == 400

# user login:
@pytest.mark.benchmark(group="users")
def test_login_performance(benchmark):
    response = benchmark(client.post, "/users/login/", json = user_data)
    assert response.status_code == 200 or response.status_code == 401

# sample data
product_data = {
    "name": "Sample Product",
    "description": "This is a sample product for testing.",
    "image": "sample.png",
    "price": 18.00
}

# adding a new product
@pytest.mark.benchmark(group = "products")
def test_add_product_performance(benchmark):
    response = benchmark(client.post, "/products/addProduct/", json = product_data)
    assert response.status_code == 200

# sample data
cartItem_data = {
    "user_id": 1,
    "product_id": 1,
    "quantity": 2
}

# add an item to cart
@pytest.mark.benchmark(group = "cart")
def test_add_item_to_cart_performance(benchmark):
    response = benchmark(client.post, "/cart/add", json = cartItem_data)
    assert response.status_code == 200

