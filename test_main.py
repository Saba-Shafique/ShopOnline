# test_main.py

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from main import app
from database import Base, init_db, DATABASE_URL

from models import User, Product, Cart, CartItem, Order, OrderItem

#  Create a new engine and sessionmaker for the test database
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency to use the test database
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Apply the override to the app
app.dependency_overrides[init_db] = override_get_db

# Initialize the test client
client = TestClient(app)

# This function will run before each test function
@pytest.fixture(autouse=True)
def setup_and_teardown():
    # Create the database tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop all tables after each test to keep tests isolated
    Base.metadata.drop_all(bind=engine)

# -------------------------------------------  USER  -------------------------------------------
# __________________________________________
# CREATE user (signup):
def test_signup_success():
    # Test successful user signup
    response = client.post(
        "/signup/",
        json={
            "email": "testuser@example.com",
            "password": "testpassword123",
            "confirm_password": "testpassword123"
        }
    )
    assert response.status_code == 200
    assert response.json()["email"] == "testuser@example.com"
    assert "id" in response.json()  # Ensure the response contains an ID

def test_signup_duplicate_email():
    # Test signup with an email that is already registered
    client.post(
        "/signup/",
        json={
            "email": "testuser@example.com",
            "password": "testpassword123",
            "confirm_password": "testpassword123"
        }
    )
    # Attempt to sign up with the same email again
    response = client.post(
        "/signup/",
        json={
            "email": "testuser@example.com",
            "password": "testpassword123",
            "confirm_password": "testpassword123"
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

def test_signup_password_mismatch():
    # Test signup with mismatched passwords
    response = client.post(
        "/signup/",
        json={
            "email": "newuser@example.com",
            "password": "testpassword123",
            "confirm_password": "differentpassword"
        }
    )
    assert response.status_code == 422
    # Update assertion to match the actual error message
    assert any(
        error["msg"] == "Value error, Passwords do not match"
        for error in response.json()["detail"]
    )

def test_signup_missing_fields():
    # Test signup with missing fields
    response = client.post(
        "/signup/",
        json={
            "email": "missingfields@example.com",
            "password": "testpassword123"
            # Missing confirm_password
        }
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "confirm_password"]
    assert response.json()["detail"][0]["msg"] == "Field required"

# __________________________________________
# READ user (login):
def test_login_success():
    client.post(
        "/signup/",
        json={
            "email": "loginuser@example.com",
            "password": "testpassword123",
            "confirm_password": "testpassword123"
        }
    )
    
    # Test successful user login
    response = client.post(
        "/login/",
        json={
            "email": "loginuser@example.com",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Login successful"
    assert "user_id" in response.json()
    assert response.json()["email"] == "loginuser@example.com"

def test_login_invalid_credentials():
    # Test login with invalid credentials
    response = client.post(
        "/login/",
        json={
            "email": "nonexistentuser@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"

def test_login_wrong_password():
    # First, sign up a user to test login with wrong password
    client.post(
        "/signup/",
        json={
            "email": "wrongpassworduser@example.com",
            "password": "correctpassword",
            "confirm_password": "correctpassword"
        }
    )
    
    # Test login with wrong password
    response = client.post(
        "/login/",
        json={
            "email": "wrongpassworduser@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"

def test_login_missing_email():
    # Test login with missing email
    response = client.post(
        "/login/",
        json={
            "password": "testpassword123"
            # Missing email
        }
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "email"]
    assert response.json()["detail"][0]["msg"] == "Field required"

def test_login_missing_password():
    # Test login with missing password
    response = client.post(
        "/login/",
        json={
            "email": "loginuser@example.com"
            # Missing password
        }
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "password"]
    assert response.json()["detail"][0]["msg"] == "Field required"


# __________________________________________
# UPDATE user (change password):
def test_update_password_success():
    # signing up a user to test password update
    client.post(
        "/signup/",
        json={
            "email": "updateuser@example.com",
            "password": "oldpassword123",
            "confirm_password": "oldpassword123"
        }
    )
    
    # Test successful password update
    response = client.put(
        "/updatePassword/",
        json={
            "email": "updateuser@example.com",
            "current_password": "oldpassword123",
            "new_password": "newpassword123",
            "confirm_new_password": "newpassword123"
        }
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Password updated successfully"

def test_update_password_invalid_current_password():
    # signing up a user to test invalid password update
    client.post(
        "/signup/",
        json={
            "email": "invalidpassworduser@example.com",
            "password": "correctpassword",
            "confirm_password": "correctpassword"
        }
    )
    
    # Test password update with incorrect current password
    response = client.put(
        "/updatePassword/",
        json={
            "email": "invalidpassworduser@example.com",
            "current_password": "wrongpassword",
            "new_password": "newpassword123",
            "confirm_new_password": "newpassword123"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or current password"

def test_update_password_mismatch():
    # signing up a user to test invalid password update
    client.post(
        "/signup/",
        json={
            "email": "mismatchuser@example.com",
            "password": "oldpassword123",
            "confirm_password": "oldpassword123"
        }
    )
    
    # Test password update with mismatched new passwords
    response = client.put(
        "/updatePassword/",
        json={
            "email": "mismatchuser@example.com",
            "current_password": "oldpassword123",
            "new_password": "newpassword123",
            "confirm_new_password": "differentnewpassword"
        }
    )
    assert response.status_code == 422
    assert any(
        error["msg"] == "Value error, New passwords do not match"
        for error in response.json()["detail"]
    )

def test_update_password_missing_new_passwords():
    # signing up a user to test invalid password update
    client.post(
        "/signup/",
        json={
            "email": "missingfeilduser@example.com",
            "password": "oldpassword123",
            "confirm_password": "oldpassword123"
        }
    )
    
    # Test password update with mismatched new passwords
    response = client.put(
        "/updatePassword/",
        json={
            "email": "missingfeilduser@example.com",
            "current_password": "oldpassword123"
            # new password and confirm password missing
        }
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "new_password"]
    assert response.json()["detail"][0]["msg"] == "Field required"

# __________________________________________
# DELETE user: (removing a user)
def test_delete_user_success():
    # Signing up a new user to test deletion
    signup_response = client.post(
        "/signup/",
        json={
            "email": "deleteuser@example.com",
            "password": "password123",
            "confirm_password": "password123"
        }
    )
    assert signup_response.status_code == 200

    # Delete the user
    delete_response = client.request(
        "DELETE",
        "/removeUser/",
        json={
            "email": "deleteuser@example.com",
            "password": "password123"
        }
    )
    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": "User and associated data successfully deleted"}

def test_delete_user_invalid_password():
    # Signing up a new user to test deletion
    signup_response = client.post(
        "/signup/",
        json={
            "email": "deleteuser@example.com",
            "password": "password123",
            "confirm_password": "password123"
        }
    )
    assert signup_response.status_code == 200
    # Attempt to delete a user with invalid password
    delete_response = client.request(
        "DELETE",
        "/removeUser/",
        json={
            "email": "deleteser@example.com",
            "password": "wrongpassword"
        }
    )
    assert delete_response.status_code == 401
    assert delete_response.json()["detail"] == "Invalid email or password"

def test_delete_user_missing_fields():
    # Attempt to delete a user with missing password
    delete_response = client.request(
        "DELETE",
        "/removeUser/",
        json={
            "email": "deleteuser@example.com"
            # Missing password field
        }
    )
    assert delete_response.status_code == 422
    assert delete_response.json()["detail"][0]["loc"] == ["body", "password"]
    assert delete_response.json()["detail"][0]["msg"] == "Field required"

    # Attempt to delete a user with missing email
    delete_response = client.request(
        "DELETE",
        "/removeUser/",
        json={
            "password": "password123"
            # Missing email field
        }
    )
    assert delete_response.status_code == 422
    assert delete_response.json()["detail"][0]["loc"] == ["body", "email"]
    assert delete_response.json()["detail"][0]["msg"] == "Field required"

# -------------------------------------------  PRODUCT  -------------------------------------------
# __________________________________________
# CREATE product: (adding a new product)
def test_create_product_success():
    response = client.post(
        "/products/addProduct/",
        json={
            "name": "Test Product",
            "description": "This is a test product.",
            "image": "https://example.com/test-product.jpg",
            "price": 29.99
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Product"
    assert data["description"] == "This is a test product."
    assert data["price"] == 29.99
    assert "id" in data 

def test_create_product_missing_fields():
    response = client.post(
        "/products/addProduct/",
        json={
            # "name": "Test Product",  # Name is missing
            "description": "This product has no name.",
            "image": "https://example.com/test-product.jpg",
            "price": 19.99
        }
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "name"]
    assert response.json()["detail"][0]["msg"] == "Field required"

def test_create_product_missing_image():
    response = client.post(
        "/products/addProduct/",
        json={
            "name": "Test Product",
            "description": "This is a test product.",
            # "image": "https://example.com/test-product.jpg",  # Image URL is missing
            "price": 19.99
        }
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "image"]
    assert response.json()["detail"][0]["msg"] == "Field required"

def test_create_product_missing_price():
    response = client.post(
        "/products/addProduct/",
        json={
            "name": "Test Product",
            "description": "This is a test product.",
            "image": "https://example.com/test-product.jpg",
            # "price": 19.99  # Price is missing
        }
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "price"]
    assert response.json()["detail"][0]["msg"] == "Field required"

def test_create_product_invalid_price():
    # Testing with string value for price
    response = client.post(
        "/products/addProduct/",
        json={
            "name": "Test Product",
            "description": "This is a test product.",
            "image": "https://example.com/test-product.jpg",
            "price": "twenty"  # Invalid price (string type)
        }
    )
    assert response.status_code == 422  # Pydantic validation error
    assert response.json()["detail"][0]["msg"] == "Input should be a valid number, unable to parse string as a number"  # Adjust based on actual Pydantic error message

# __________________________________________
# READ product: (get all products, by id, by name)
def test_read_all_products_success():
    # Add products to the database for testing
    client.post(
        "/products/addProduct/",
        json={
            "name": "Product 1",
            "description": "Description 1",
            "image": "https://example.com/product1.jpg",
            "price": 19.99
        }
    )
    client.post(
        "/products/addProduct/",
        json={
            "name": "Product 2",
            "description": "Description 2",
            "image": "https://example.com/product2.jpg",
            "price": 29.99
        }
    )
    
    # Test reading all products
    response = client.get("/products/allProducts")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 2  # Ensure there are two products returned
    assert data[0]["name"] == "Product 1"
    assert data[1]["name"] == "Product 2"

def test_read_all_products_empty():
    # Ensure the database is empty
    response = client.get("/products/allProducts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0  # Expecting no products

def test_read_product_by_id_success():
    # Add a product to the database for testing
    create_response = client.post(
        "/products/addProduct/",
        json={
            "name": "Test Product",
            "description": "This is a test product.",
            "image": "https://example.com/test-product.jpg",
            "price": 29.99
        }
    )
    product_id = create_response.json()["id"]
    
    # Test retrieving the product by ID
    response = client.get(f"/products/byId/{product_id}")
    assert response.status_code == 200
    data = response.json()
    
    assert data["name"] == "Test Product"
    assert data["description"] == "This is a test product."
    assert data["price"] == 29.99

def test_read_product_by_invalid_id():
    # Test retrieving a product with an invalid ID
    response = client.get("/products/byId/9999")  # Assuming ID 9999 doesn't exist
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"

def test_read_products_by_name_success():
    # Add products to the database for testing
    client.post(
        "/products/addProduct/",
        json={
            "name": "Product 1",
            "description": "Poduct 1 for testing",
            "image": "https://example.com/unique-product.jpg",
            "price": 39.99
        }
    )
    client.post(
        "/products/addProduct/",
        json={
            "name": "Product 2",
            "description": "Poduct 1 for testing",
            "image": "https://example.com/another-product.jpg",
            "price": 49.99
        }
    )
    
    # Test retrieving products by name
    response = client.get("/products/byName/?name=Product 1")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 1
    assert data[0]["name"] == "Product 1"

def test_read_products_by_name_no_matches():
    # Test retrieving products by a name that doesn't match any product
    response = client.get("/products/byName/?name=Nonexistent")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0  # No products should match

def test_read_products_by_name_missing_query():
    # Test retrieving products without a name query parameter
    response = client.get("/products/byName/")
    assert response.status_code == 400
    assert response.json()["detail"] == "Query parameter 'name' is required"

# __________________________________________
# UPDATE product: (update any of the entery of a product)
def test_update_product_success():
    # First, create a product to update
    create_response = client.post(
        "/products/addProduct/",
        json={
            "name": "Old Product",
            "description": "Old description",
            "image": "https://example.com/old-product.jpg",
            "price": 19.99
        }
    )
    product_id = create_response.json()["id"]

    # Update the product with new details
    update_response = client.put(
        f"/products/updateProduct/{product_id}",
        json={
            "name": "Updated Product",
            "description": "Updated description",
            "image": "https://example.com/updated-product.jpg",
            "price": 29.99
        }
    )
    assert update_response.status_code == 200
    data = update_response.json()

    assert data["name"] == "Updated Product"
    assert data["description"] == "Updated description"
    assert data["image"] == "https://example.com/updated-product.jpg"
    assert data["price"] == 29.99
    assert "id" in data
    assert data["id"] == product_id

# __________________________________________
# DELETE product: (Remove a product)
def test_delete_product_success():
    # Create a product to delete
    response = client.post(
        "/products/addProduct/",
        json={
            "name": "Product to Delete",
            "description": "This product will be deleted",
            "image": "https://example.com/product-to-delete.jpg",
            "price": 9.99
        }
    )
    assert response.status_code == 200
    product_id = response.json()["id"]

    # Delete the product
    delete_response = client.delete(f"/products/remove/{product_id}")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"detail": "Product deleted successfully"}

    # Verify the product is deleted
    get_response = client.get(f"/products/byId/{product_id}")
    assert get_response.status_code == 404
    assert get_response.json() == {"detail": "Product not found"}

def test_delete_product_not_found():
    non_existent_product_id = 9999  # Use an ID that is not present in the database
    response = client.delete(f"/products/remove/{non_existent_product_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}

# -------------------------------------------  CART & CART-ITEMS  -------------------------------------------
# __________________________________________
# add product to cart:
def test_add_to_cart():
    # Create a user
    response = client.post(
        "/signup/",
        json={
            "email": "john@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
    )
    assert response.status_code == 200  # Ensure the request is successful
    user = response.json()
    assert "id" in user  # Check if the user response contains an 'id'
    user_id = user["id"]

    # Create a product
    response = client.post(
        "/products/addProduct/",
        json={
            "name": "Sample Product",
            "description": "A great product",
            "image": "image_url",
            "price": 100.0,
        },
    )
    assert response.status_code == 200
    product = response.json()
    assert "id" in product
    product_id = product["id"]

    # Add product to cart
    response = client.post(
        "/cart/add",
        json={"user_id": user_id, "product_id": product_id, "quantity": 2},
    )
    assert response.status_code == 200
    cart = response.json()

    # Assert the cart details
    assert cart["total_price"] == 200.0
    assert len(cart["items"]) == 1
    assert cart["items"][0]["product_id"] == product_id
    assert cart["items"][0]["quantity"] == 2
    assert cart["items"][0]["total_price"] == 200.0

def test_add_to_cart_user_not_found():
    # Try adding a product to a cart for a non-existent user
    response = client.post(
        "/cart/add",
        json={
            "user_id": 99999,  # Non-existent user ID
            "product_id": 1,
            "quantity": 1,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

def test_add_to_cart_product_not_found():
    # Create a user
    response = client.post(
        "/signup/",
        json={
            "email": "jane@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
    )
    assert response.status_code == 200
    user = response.json()
    user_id = user["id"]

    # Try adding a non-existent product to a cart
    response = client.post(
        "/cart/add",
        json={
            "user_id": user_id,
            "product_id": 99999,  # Non-existent product ID
            "quantity": 1,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"

def test_add_to_cart_invalid_quantity():
    # Create a user
    response = client.post(
        "/signup/",
        json={
            "email": "doe@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
    )
    assert response.status_code == 200
    user = response.json()
    user_id = user["id"]

    # Create a product
    response = client.post(
        "/products/addProduct/",
        json={
            "name": "Another Product",
            "description": "Another great product",
            "image": "another_image_url",
            "price": 50.0,
        },
    )
    assert response.status_code == 200
    product = response.json()
    product_id = product["id"]

    # Try adding the product to cart with invalid quantity
    response = client.post(
        "/cart/add",
        json={
            "user_id": user_id,
            "product_id": product_id,
            "quantity": 0,  # Invalid quantity
        },
    )
    assert response.status_code == 400  # Expecting 400 Bad Request
    assert response.json()["detail"] == "Quantity must be greater than zero"

    # Try adding the product to cart with negative quantity
    response = client.post(
        "/cart/add",
        json={
            "user_id": user_id,
            "product_id": product_id,
            "quantity": -5,  # Invalid negative quantity
        },
    )
    assert response.status_code == 400  # Expecting 400 Bad Request
    assert response.json()["detail"] == "Quantity must be greater than zero"

# __________________________________________
# READ: View cart items
def test_view_cart_with_items():
    # Create a user
    response = client.post(
        "/signup/",
        json={
            "email": "john@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
    )
    assert response.status_code == 200
    user = response.json()
    user_id = user["id"]

    # Create a product
    response = client.post(
        "/products/addProduct/",
        json={
            "name": "Sample Product",
            "description": "A great product",
            "image": "image_url",
            "price": 100.0,
        },
    )
    assert response.status_code == 200
    product = response.json()
    product_id = product["id"]

    # Add product to cart
    response = client.post(
        "/cart/add",
        json={"user_id": user_id, "product_id": product_id, "quantity": 2},
    )
    assert response.status_code == 200

    # View the cart
    response = client.get(f"/cart/?user_id={user_id}")
    assert response.status_code == 200
    cart = response.json()

    # Assert the cart details
    assert cart["total_price"] == 200.0
    assert len(cart["items"]) == 1
    assert cart["items"][0]["product_id"] == product_id
    assert cart["items"][0]["quantity"] == 2
    assert cart["items"][0]["total_price"] == 200.0

def test_view_empty_cart():
    # Create a user
    response = client.post(
        "/signup/",
        json={
            "email": "jane@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
    )
    assert response.status_code == 200
    user = response.json()
    user_id = user["id"]

    # View the cart
    response = client.get(f"/cart/?user_id={user_id}")
    assert response.status_code == 200
    cart = response.json()

    # Assert the cart is empty
    assert cart["total_price"] == 0.0
    assert len(cart["items"]) == 0

def test_view_cart_user_not_found():
    # Attempt to view a cart for a non-existent user
    response = client.get("/cart/?user_id=99999")  # Non-existent user ID
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

def test_view_cart_cart_not_found():
    # Create a user without a cart
    response = client.post(
        "/signup/",
        json={
            "email": "doe@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
    )
    assert response.status_code == 200
    user = response.json()
    user_id = user["id"]

    # Directly delete the cart to simulate cart not found
    db = next(override_get_db())
    db_user = db.query(User).filter(User.id == user_id).first()
    db.delete(db_user.cart)
    db.commit()

    # Attempt to view the cart
    response = client.get(f"/cart/?user_id={user_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Cart not found"

# __________________________________________
# # UPDATE cart item (uodate quantity)
def test_update_cart_item_success():
    # Create a user
    response = client.post("/signup/", json={
        "email": "updateuser@example.com",
        "password": "password123",
        "confirm_password": "password123"
    })
    assert response.status_code == 200
    user = response.json()
    user_id = user["id"]

    # Create a product
    response = client.post("/products/addProduct/", json={
        "name": "Product Update Test",
        "description": "A product for testing update",
        "image": "image_url",
        "price": 50.0
    })
    assert response.status_code == 200
    product = response.json()
    product_id = product["id"]

    # Add product to cart
    response = client.post("/cart/add", json={
        "user_id": user_id,
        "product_id": product_id,
        "quantity": 2
    })
    assert response.status_code == 200
    cart = response.json()
    cart_item_id = cart["items"][0]["id"]

    # Update the cart item
    response = client.put(f"/cart/update/{cart_item_id}", json={
        "quantity": 3
    }, params={"user_id": user_id})
    assert response.status_code == 200
    updated_cart = response.json()

    # Assert the cart item details
    assert updated_cart["total_price"] == 150.0
    assert len(updated_cart["items"]) == 1
    assert updated_cart["items"][0]["quantity"] == 3
    assert updated_cart["items"][0]["total_price"] == 150.0

def test_update_cart_item_not_found():
    # Create a user
    response = client.post("/signup/", json={
        "email": "cartitemnotfound@example.com",
        "password": "password123",
        "confirm_password": "password123"
    })
    assert response.status_code == 200
    user = response.json()
    user_id = user["id"]

    # Try updating a non-existent cart item
    response = client.put("/cart/update/99999", json={
        "quantity": 3
    }, params={"user_id": user_id})
    assert response.status_code == 404
    assert response.json()["detail"] == "Cart item not found"

def test_update_cart_item_product_not_found():
    # Create a user
    response = client.post("/signup/", json={
        "email": "productnotfound@example.com",
        "password": "password123",
        "confirm_password": "password123"
    })
    assert response.status_code == 200
    user = response.json()
    user_id = user["id"]

    # Add product to cart
    response = client.post("/cart/add", json={
        "user_id": user_id,
        "product_id": 1,  # Assuming this product_id does not exist
        "quantity": 2
    })
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"

def test_update_cart_item_invalid_quantity():
    # Create a user
    response = client.post("/signup/", json={
        "email": "invalidquantity@example.com",
        "password": "password123",
        "confirm_password": "password123"
    })
    assert response.status_code == 200
    user = response.json()
    user_id = user["id"]

    # Create a product
    response = client.post("/products/addProduct/", json={
        "name": "Invalid Quantity Product",
        "description": "A product for testing invalid quantity",
        "image": "image_url",
        "price": 70.0
    })
    assert response.status_code == 200
    product = response.json()
    product_id = product["id"]

    # Add product to cart
    response = client.post("/cart/add", json={
        "user_id": user_id,
        "product_id": product_id,
        "quantity": 2
    })
    assert response.status_code == 200
    cart = response.json()
    cart_item_id = cart["items"][0]["id"]

    # Try updating the cart item with invalid quantity
    response = client.put(f"/cart/update/{cart_item_id}", json={
        "quantity": -1
    }, params={"user_id": user_id})
    
    # Check for invalid quantity response
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid quantity"

#  __________________________________________
# DELETE item from cart
def test_remove_cart_item_success():
    # Create a user
    response = client.post("/signup/", json={
        "email": "deleteitem@example.com",
        "password": "password123",
        "confirm_password": "password123"
    })
    assert response.status_code == 200
    user = response.json()
    user_id = user["id"]

    # Create a product
    response = client.post("/products/addProduct/", json={
        "name": "Removable Product",
        "description": "A product to be removed",
        "image": "image_url",
        "price": 50.0
    })
    assert response.status_code == 200
    product = response.json()
    product_id = product["id"]

    # Add product to cart
    response = client.post("/cart/add", json={
        "user_id": user_id,
        "product_id": product_id,
        "quantity": 2
    })
    assert response.status_code == 200
    cart = response.json()
    cart_item_id = cart["items"][0]["id"]

    # Remove the cart item
    response = client.delete(f"/cart/remove?item_id={cart_item_id}&user_id={user_id}")
    assert response.status_code == 200
    updated_cart = response.json()
    assert len(updated_cart["items"]) == 0
    assert updated_cart["total_price"] == 0.0

def test_remove_cart_item_not_found():
    # Attempt to remove a non-existent cart item
    response = client.delete("/cart/remove", params={
        "item_id": 9999,  # Assuming 9999 does not exist
        "user_id": 1  # Assuming user_id 1 exists
    })
    assert response.status_code == 404
    assert response.json()["detail"] == "Cart item not found"

def test_remove_cart_item_user_not_found():
    # Create a product
    response = client.post("/products/addProduct/", json={
        "name": "Product to Remove",
        "description": "A product for testing",
        "image": "image_url",
        "price": 75.0
    })
    assert response.status_code == 200
    product = response.json()
    product_id = product["id"]

    # Create a user and add a product to cart
    response = client.post("/signup/", json={
        "email": "userforremoval@example.com",
        "password": "password123",
        "confirm_password": "password123"
    })
    assert response.status_code == 200
    user = response.json()
    user_id = user["id"]

    response = client.post("/cart/add", json={
        "user_id": user_id,
        "product_id": product_id,
        "quantity": 1
    })
    assert response.status_code == 200
    cart = response.json()
    cart_item_id = cart["items"][0]["id"]

    # Attempt to remove the cart item with a non-existent user
    response = client.delete(f"/cart/remove?item_id={cart_item_id}&user_id=9999")  # Assuming 9999 does not exist
    assert response.status_code == 404
    assert response.json()["detail"] == "Cart not found"

#  __________________________________________
# INCREMENT an item
def test_increment_cart_item_success():
    # Create a user
    response = client.post("/signup/", json={
        "email": "incrementuser@example.com",
        "password": "password123",
        "confirm_password": "password123"
    })
    assert response.status_code == 200
    user = response.json()
    user_id = user["id"]

    # Create a product
    response = client.post("/products/addProduct/", json={
        "name": "Increment Product",
        "description": "A product to increment",
        "image": "image_url",
        "price": 25.0
    })
    assert response.status_code == 200
    product = response.json()
    product_id = product["id"]

    # Add product to cart
    response = client.post("/cart/add", json={
        "user_id": user_id,
        "product_id": product_id,
        "quantity": 1
    })
    assert response.status_code == 200
    cart = response.json()
    cart_item_id = cart["items"][0]["id"]

    # Increment the cart item
    response = client.put("/cart/increment", json={
        "item_id": cart_item_id,
        "user_id": user_id
    })
    assert response.status_code == 200
    updated_cart = response.json()
    assert updated_cart["total_price"] == 50.0  # Price should be updated to 25.0 * 2
    assert len(updated_cart["items"]) == 1
    assert updated_cart["items"][0]["quantity"] == 2  # Quantity should be incremented

def test_increment_cart_item_not_found():
    # Attempt to increment a non-existent cart item
    response = client.put("/cart/increment", json={
        "item_id": 9999,  # Assuming this ID does not exist
        "user_id": 1  # Assuming this user ID exists
    })
    assert response.status_code == 404
    assert response.json()["detail"] == "Cart item not found"

#  __________________________________________
# DECREMENT an item
def test_decrement_cart_item_success():
    # Create a user
    response = client.post("/signup/", json={
        "email": "decrementuser@example.com",
        "password": "password123",
        "confirm_password": "password123"
    })
    assert response.status_code == 200
    user = response.json()
    user_id = user["id"]

    # Create a product
    response = client.post("/products/addProduct/", json={
        "name": "Decrement Product",
        "description": "A product to decrement",
        "image": "image_url",
        "price": 30.0
    })
    assert response.status_code == 200
    product = response.json()
    product_id = product["id"]

    # Add product to cart
    response = client.post("/cart/add", json={
        "user_id": user_id,
        "product_id": product_id,
        "quantity": 2
    })
    assert response.status_code == 200
    cart = response.json()
    cart_item_id = cart["items"][0]["id"]

    # Decrement the cart item
    response = client.put("/cart/decrement", json={
        "item_id": cart_item_id,
        "user_id": user_id
    })
    assert response.status_code == 200
    updated_cart = response.json()
    assert updated_cart["total_price"] == 30.0  # Price should be updated to 30.0
    assert len(updated_cart["items"]) == 1
    assert updated_cart["items"][0]["quantity"] == 1  # Quantity should be decremented to 1

# -------------------------------------------  ORDER & ORDER-ITEMS  -------------------------------------------
# __________________________________________
# CREATE order:
# def test_place_order():
#     # Create a user
#     response = client.post(
#         "/signup/",
#         json={
#             "email": "john@example.com",
#             "password": "password123",
#             "confirm_password": "password123",
#         },
#     )
#     assert response.status_code == 200
#     user = response.json()
#     assert "id" in user
#     user_id = user["id"]

#     # Create a product
#     response = client.post(
#         "/products/addProduct/",
#         json={
#             "name": "Sample Product",
#             "description": "A great product",
#             "image": "image_url",
#             "price": 100.0,
#         },
#     )
#     assert response.status_code == 200
#     product = response.json()
#     assert "id" in product
#     product_id = product["id"]

#     # Add product to cart
#     response = client.post(
#         "/cart/add",
#         json={"user_id": user_id, "product_id": product_id, "quantity": 2},
#     )
#     assert response.status_code == 200
#     cart = response.json()

#     # Ensure the cart has the correct total price and items
#     assert cart["total_price"] == 200.0
#     assert len(cart["items"]) == 1
#     cart_id = cart["id"]  # Get the cart id for order placement

#     # Place an order
#     response = client.post(
#         "/orders/placeOrder/",
#         json={"user_id": user_id, "cart_id": cart_id}  # Send cart_id as part of the request body
#     )
#     assert response.status_code == 200
#     order = response.json()

#     # Verify the order details
#     assert "id" in order
#     assert order["user_id"] == user_id
#     assert order["total_amount"] == 200.0  # The total amount should match the cart total

#     # Verify that the cart has been cleared
#     response = client.get(f"/cart/{cart_id}")
#     assert response.status_code == 200
#     updated_cart = response.json()
#     assert updated_cart["total_price"] == 0.0
#     assert len(updated_cart["items"]) == 0
