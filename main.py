from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, EmailStr, field_validator, ValidationInfo, validator
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from models import User, Cart, CartItem, Product, Order, OrderItem
from database import SessionLocal, init_db
from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles

from google.oauth2 import id_token
from google.auth.transport import requests

import shutil   # file operations for handling file copying, moving, removing, and directory management tasks. 
import os


app = FastAPI()

GOOGLE_CLIENT_ID = "729091295543-ntjssfpmlq0c09oiav7sdl9cm1gdl34g.apps.googleusercontent.com"

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  
    allow_credentials=True,
    allow_methods=["*"],  # all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"], 
)

# Initialize the database
init_db()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Route to display a welcome message
@app.get("/")
def read_root():
    return {"message": "Welcome to the shopOnline API!"}

# -------------------------------------------  USER  -------------------------------------------
# Pydantic model for signup requests
class UserSignup(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str

    @field_validator('confirm_password')
    def passwords_match(cls, confirm_password, info: ValidationInfo):
        # Validate that password and confirm_password match
        if 'password' in info.data and confirm_password != info.data['password']:
            raise ValueError('Passwords do not match')
        return confirm_password

# Pydantic model for login requests
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Pydantic model for user deletion requests
class UserDelete(BaseModel):
    email: EmailStr
    password: str

# Pydantic model for updating user password
class UserPasswordUpdate(BaseModel):
    email: EmailStr
    current_password: str
    new_password: str
    confirm_new_password: str

    @field_validator('confirm_new_password')
    def passwords_match(cls, confirm_new_password, info: ValidationInfo):
        # Validate that new_password and confirm_new_password match
        if 'new_password' in info.data and confirm_new_password != info.data['new_password']:
            raise ValueError('New passwords do not match')
        return confirm_new_password

# Pydantic model for displaying user data
class UserResponse(BaseModel):
    id: int
    email: str

    class Config:
        from_attributes = True  # Use 'from_attributes' instead of 'orm_mode'

class GoogleLogin(BaseModel):
    token: str

@app.post("/google-login/")
def google_login(google_login: GoogleLogin, db: Session = Depends(get_db)):
    try:
        # Verify the Google JWT token
        idinfo = id_token.verify_oauth2_token(google_login.token, requests.Request(), GOOGLE_CLIENT_ID)

        # Check if the user exists in the database
        user_email = idinfo['email']
        db_user = db.query(User).filter(User.email == user_email).first()

        if not db_user:
            # If the user does not exist, create a new user
            db_user = User(email=user_email)
            db.add(db_user)
            db.commit()
            db.refresh(db_user)

            # Create an associated cart for the new user
            new_cart = Cart(user=db_user)
            db.add(new_cart)
            db.commit()

        # Ensure the user has a cart (for existing users)
        if not db_user.cart:
            new_cart = Cart(user=db_user)
            db.add(new_cart)
            db.commit()
            db.refresh(new_cart)

        return {"message": "Login successful", "user_id": db_user.id, "email": db_user.email}
    
    except ValueError:
        # Invalid token
        raise HTTPException(status_code=401, detail="Invalid token")

# Route to sign up a new user
@app.post("/signup/", response_model=UserResponse)
def sign_up(user: UserSignup, db: Session = Depends(get_db)):
    # Check if the email is already registered
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create a new user
    new_user = User(email=user.email, password=user.password)
    db.add(new_user)

    try:
        db.commit()
        db.refresh(new_user)  # Refresh to get the new user's ID
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Could not create user due to integrity error")

    # Create a cart for the new user
    if not new_user.cart:
        new_cart = Cart(user=new_user)
        db.add(new_cart)
        db.commit()
        db.refresh(new_cart)

    # Return the response with the correct field names
    return {"id": new_user.id, "email": new_user.email}

# Route to login a user
@app.post("/login/")
def login(user: UserLogin, db: Session = Depends(get_db)):
    # Check if the user exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Check if the password is correct
    if db_user.password != user.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Ensure the user has a cart
    if not db_user.cart:
        new_cart = Cart(user=db_user)
        db.add(new_cart)
        db.commit()
        db.refresh(new_cart)  # Refresh to get the new cart ID

    return {"message": "Login successful", "user_id": db_user.id, "email": db_user.email}

# Route to delete a user by email and password
@app.delete("/removeUser/")
def delete_user(user: UserDelete, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email, User.password == user.password).first()
    if db_user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Access and delete user's cart through the User relationship
    if db_user.cart:
        db.delete(db_user.cart)
        
    # Also delete the user's orders and associated order items if necessary
    user_orders = db.query(Order).filter(Order.user_id == db_user.id).all()
    for order in user_orders:
        # Delete associated order items
        db.query(OrderItem).filter(OrderItem.order_id == order.id).delete()
        db.delete(order)
    
    # Finally, delete the user
    db.delete(db_user)

    try:
        db.commit()
        return {"message": "User and associated data successfully deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred while deleting the user: {str(e)}")
    
# Route to update the user's password
@app.put("/updatePassword/")
def update_password(data: UserPasswordUpdate, db: Session = Depends(get_db)):
    # Fetch the user by email and current password
    db_user = db.query(User).filter(User.email == data.email, User.password == data.current_password).first()
    
    if db_user is None:
        raise HTTPException(status_code=401, detail="Invalid email or current password")
    
    # Update the user's password
    db_user.password = data.new_password
    db.commit()
    db.refresh(db_user)

    return {"message": "Password updated successfully"}

# # -------------------------------------------------------------------------------------------------

# # -------------------------------------------  PRODUCT  -------------------------------------------
# __________________________________________
# Pydantic model for creating a product
class ProductCreate(BaseModel):
    name: str
    category: str  # Replace description with category
    price: float

# Pydantic model for product response
class ProductResponse(BaseModel):
    id: int
    name: str
    category: str  # Replace description with category
    image: str
    price: float

    class Config:
        from_attributes = True

# Create a new product and save its image
@app.post("/addProduct", response_model=ProductResponse)
async def create_product(
    name: str,
    category: str,
    price: float,
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    upload_dir = 'static/images/products'
    os.makedirs(upload_dir, exist_ok=True)

    if not image.filename.endswith(('.png', '.jpg', '.jpeg')):
        raise HTTPException(status_code=400, detail="Invalid image format. Please upload a PNG or JPEG image.")

    image_path = os.path.join(upload_dir, image.filename)
    with open(image_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    new_product = Product(name=name, category=category, image=image_path, price=price)
    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    return new_product


# __________________________________________
# READ products:

# Serve static files from the "frontend/src/assets" directory
app.mount("/static", StaticFiles(directory= "frontend/src/assets"), name="static")

@app.get("/products/", response_model=List[ProductResponse])
def read_products(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return products

@app.get("/products", response_model=List[ProductResponse])
def read_products(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return products

@app.get("/products/byName/", response_model=List[ProductResponse])
def read_products_by_name(name: Optional[str] = None, db: Session = Depends(get_db)):
    if name is None:
        raise HTTPException(status_code=400, detail="Query parameter 'name' is required")
    
    products = db.query(Product).filter(Product.name.ilike(f"%{name}%")).all()
    
    if not products:
        raise HTTPException(status_code=404, detail="No products found with the given name.")
    
    return products

@app.get("/products/byId/{product_id}", response_model=ProductResponse)
def read_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.get("/products/byCategory/", response_model=List[ProductResponse])
def read_products_by_category(category: Optional[str] = None, db: Session = Depends(get_db)):
    if category is None:
        raise HTTPException(status_code=400, detail="Query parameter 'category' is required")
    products = db.query(Product).filter(Product.category.ilike(f"%{category}%")).all()
    if not products:
        raise HTTPException(status_code=404, detail="No products found for the specified category")
    return products

# __________________________________________
# UPDATE a product:
@app.put("/products/updateProduct/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product: ProductCreate, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db_product.name = product.name
    db_product.category = product.category  # Update category instead of description
    db_product.price = product.price

    db.commit()
    db.refresh(db_product)
    return db_product

# __________________________________________
# DELETE a product:
@app.delete("/products/remove/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(db_product)
    db.commit()
    return {"detail": "Product deleted successfully"}

# # ----------------------------------------------------------------------------------------------------------
# # -------------------------------------------  CART & CART-ITEM  -------------------------------------------
class CartItemCreate(BaseModel):
    user_id: int 
    product_id: int
    quantity: int

# Pydantic model for updating cart item
class CartItemUpdate(BaseModel):
    quantity: int

class RemoveCartItemRequest(BaseModel):
    user_id: int
    item_id: int

# Pydantic model for decrement request
class DecrementRequest(BaseModel):
    item_id: int
    user_id: int

# Pydantic model for increment request
class IncrementRequest(BaseModel):
    user_id: int
    item_id: int

class CartItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    price: float
    total_price: float
    product_name: str  # Add this line
    product_image: str  # Add this line

    class Config:
        orm_mode = True

class CartResponse(BaseModel):
    id: int
    total_price: float
    items: List[CartItemResponse] = []

    class Config:
        from_attributes = True

# __________________________________________
# Add product to cart
@app.post("/cart/add", response_model=CartResponse)
def add_to_cart(item: CartItemCreate, db: Session = Depends(get_db)):
    # Log incoming request data for debugging
    print(f"Received item: {item}")

    # Validate quantity
    if item.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than zero")

    user_id = item.user_id
    # Retrieve the user's cart
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Retrieve the product
    product = db.query(Product).filter(Product.id == item.product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check if item already in cart
    cart_item = db.query(CartItem).filter(
        CartItem.cart_id == db_user.cart.id, CartItem.product_id == item.product_id
    ).first()
    if cart_item:
        cart_item.quantity += item.quantity
        cart_item.total_price = cart_item.quantity * product.price
    else:
        # Create a new cart item
        cart_item = CartItem(
            cart_id=db_user.cart.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=product.price,
            total_price=item.quantity * product.price,
        )
        db.add(cart_item)

    # Update cart total price
    db_user.cart.total_price += item.quantity * product.price

    # Commit the transaction
    db.commit()

    # Refresh the cart
    db.refresh(db_user.cart)

    # Log the updated cart for debugging
    print(f"Updated cart: {db_user.cart}")

    return db_user.cart

@app.post("/cart/update", response_model=CartResponse)
def update_cart(item: CartItemUpdate, db: Session = Depends(get_db)):
    # Validate quantity
    if item.quantity == 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than zero")

    user_id = item.user_id
    # Retrieve the user's cart
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Retrieve the product
    product = db.query(Product).filter(Product.id == item.product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    # Retrieve or create the cart item
    cart_item = db.query(CartItem).filter(
        CartItem.cart_id == db_user.cart.id, CartItem.product_id == item.product_id
    ).first()

    if cart_item:
        if item.quantity > 0:
            cart_item.quantity += item.quantity
            cart_item.total_price = cart_item.quantity * product.price
        else:
            db.delete(cart_item)
    else:
        if item.quantity > 0:
            cart_item = CartItem(
                cart_id=db_user.cart.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=product.price,
                total_price=item.quantity * product.price,
            )
            db.add(cart_item)

    # Update cart total price
    db_user.cart.total_price += item.quantity * product.price

    # Commit the transaction
    db.commit()
    db.refresh(db_user.cart)

    return db_user.cart


#  __________________________________________
# READ: View cart items
@app.get("/cart/")
def get_cart(user_id: int, db: Session = Depends(get_db)):
    # Retrieve the user's cart
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None or db_user.cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")

    # Return cart details
    cart = db_user.cart
    items = (
        db.query(CartItem)
        .join(Product, CartItem.product_id == Product.id)
        .filter(CartItem.cart_id == cart.id)
        .order_by(CartItem.id)  # Ensure items are ordered by their ID
        .all()
    )
    total_price = sum(item.total_price for item in items)

    return {
        "id": cart.id,
        "total_price": total_price,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price": item.price,
                "total_price": item.total_price,
                "product_name": item.product.name,  # Add product name
                "product_image": item.product.image,  # Add product image
            }
            for item in items
        ],
    }

#  __________________________________________
# UPDATE cart item (uodate quantity)
@app.put("/cart/update/{item_id}", response_model=CartResponse)
def update_cart_item(item_id: int, quantity_update: CartItemUpdate, user_id: int = Query(...), db: Session = Depends(get_db)):
    # Retrieve the cart item
    cart_item = db.query(CartItem).filter(CartItem.id == item_id).first()
    if cart_item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")

    # Retrieve the user's cart
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None or db_user.cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")

    # Retrieve the product to get the price
    product = db.query(Product).filter(Product.id == cart_item.product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    # Validate the quantity
    if quantity_update.quantity <= 0:
        raise HTTPException(status_code=400, detail="Invalid quantity")

    # Update the cart item quantity and total price
    cart_item.quantity = quantity_update.quantity
    cart_item.total_price = quantity_update.quantity * product.price

    # Update cart total price
    cart = db_user.cart
    cart.total_price = sum(item.total_price for item in db.query(CartItem).filter(CartItem.cart_id == cart.id).all())

    # Commit the transaction
    db.commit()
    db.refresh(cart)

    return CartResponse(
        id=cart.id,
        total_price=cart.total_price,
        items=[CartItemResponse(
            id=item.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.price,
            total_price=item.total_price
        ) for item in db.query(CartItem).filter(CartItem.cart_id == cart.id).all()]
    )

# reset cart to an empty cart:
@app.put("/cart/reset/{user_id}")
def reset_cart(user_id: int, db: Session = Depends(get_db)):
    # Retrieve the user's cart
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None or db_user.cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")

    # Retrieve all cart items
    cart_items = db.query(CartItem).filter(CartItem.cart_id == db_user.cart.id).all()

    # Delete all cart items
    for item in cart_items:
        db.delete(item)

    # Reset cart total price to 0
    db_user.cart.total_price = 0

    # Commit the transaction
    db.commit()
    db.refresh(db_user.cart)

    return db_user.cart

# DELETE item from cart
@app.delete("/cart/remove", response_model=CartResponse)
def remove_cart_item(item_id: int = Query(...), user_id: int = Query(...), db: Session = Depends(get_db)):
    # Retrieve the cart item
    cart_item = db.query(CartItem).filter(CartItem.id == item_id).first()
    if cart_item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")

    # Retrieve the user's cart
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None or db_user.cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")

    # Update cart total price
    cart = db_user.cart
    cart.total_price -= cart_item.total_price

    # Delete the cart item
    db.delete(cart_item)
    db.commit()
    db.refresh(cart)

    # Prepare the response data
    cart_items_response = [
        CartItemResponse(
            id=item.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.price,
            total_price=item.total_price,
            product_name=item.product.name,  # Include product name
            product_image=item.product.image,  # Include product image
        )
        for item in db.query(CartItem).filter(CartItem.cart_id == cart.id).all()
    ]

    return CartResponse(
        id=cart.id,
        total_price=cart.total_price,
        items=cart_items_response
    )

#  __________________________________________
#  __________________________________________
# INCREMENT an item
@app.put("/cart/increment", response_model=CartResponse)
def increment_cart_item(request: IncrementRequest, db: Session = Depends(get_db)):
    # Retrieve the cart item
    cart_item = db.query(CartItem).filter(CartItem.id == request.item_id).first()
    if cart_item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")

    # Retrieve the user's cart
    db_user = db.query(User).filter(User.id == request.user_id).first()
    if db_user is None or db_user.cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")

    # Retrieve the product to get the price
    product = db.query(Product).filter(Product.id == cart_item.product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    # Increment the cart item quantity and update total price
    cart_item.quantity += 1
    cart_item.total_price = cart_item.quantity * product.price

    # Update cart total price
    cart = db_user.cart
    cart.total_price = sum(
        item.total_price for item in db.query(CartItem).filter(CartItem.cart_id == cart.id).all()
    )

    # Commit the transaction
    db.commit()
    db.refresh(cart)

    return CartResponse(
        id=cart.id,
        total_price=cart.total_price,
        items=[
            CartItemResponse(
                id=item.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.price,
                total_price=item.total_price,
                product_name=item.product.name,  # Include product name
                product_image=item.product.image,  # Include product image
            )
            for item in db.query(CartItem).filter(CartItem.cart_id == cart.id).all()
        ],
    )

#  __________________________________________
# DECREMENT an item
@app.put("/cart/decrement", response_model=CartResponse)
def decrement_cart_item(request: DecrementRequest, db: Session = Depends(get_db)):
    # Retrieve the cart item
    cart_item = db.query(CartItem).filter(CartItem.id == request.item_id).first()
    if cart_item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")

    # Retrieve the user's cart
    db_user = db.query(User).filter(User.id == request.user_id).first()
    if db_user is None or db_user.cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")

    # Retrieve the product to get the price
    product = db.query(Product).filter(Product.id == cart_item.product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    # Decrement the cart item quantity if greater than 1
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.total_price = cart_item.quantity * product.price

        # Update cart total price
        cart = db_user.cart
        cart.total_price = sum(
            item.total_price for item in db.query(CartItem).filter(CartItem.cart_id == cart.id).all()
        )

        # Commit the transaction
        db.commit()
        db.refresh(cart)
    else:
        # If the quantity is 1, do nothing
        cart = db_user.cart

    # Prepare the response data
    cart_items_response = [
        CartItemResponse(
            id=item.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.price,
            total_price=item.total_price,
            product_name=item.product.name,  # Include product name
            product_image=item.product.image,  # Include product image
        )
        for item in db.query(CartItem).filter(CartItem.cart_id == cart.id).all()
    ]

    return CartResponse(
        id=cart.id,
        total_price=cart.total_price,
        items=cart_items_response,
    )

# # ------------------------------------------------------------------------------------------------------------
# # -------------------------------------------  ORDER & ORDER-ITEM  -------------------------------------------

#           WHEN THE USER CLICKS ORDER BUTTON GIVE CART SUMMARY AND A BUTTON "ORDER"

# pydantic models:
# class OrderItemBase(BaseModel):
#     product_id: int
#     quantity: int
#     price: float
#     total_price: float

#     class Config:
#         orm_mode = True

# class OrderBase(BaseModel):
#     user_id: int
#     total_amount: float

#     class Config:
#         orm_mode = True

# class OrderCreate(OrderBase):
#     pass

# class Order(OrderBase):
#     id: int
#     items: List[OrderItemBase] = []

#     class Config:
#         orm_mode = True

# class OrderItem(OrderItemBase):
#     id: int
#     order_id: int

#     class Config:
#         orm_mode = True

# class OrderRequest(BaseModel):
#     user_id: int
#     cart_id: int

#  __________________________________________
# # # READ an order
# # @app.get("/orders/{user_id}", response_model=List[Order])
# # def get_orders(user_id: int, db: Session = Depends(get_db)):
# #     orders = db.query(Order).filter(Order.user_id == user_id).all()
# #     if not orders:
# #         raise HTTPException(status_code=404, detail="No orders found for this user")
# #     return orders

# # @app.get("/orders/{order_id}", response_model=Order)
# # def get_order(order_id: int, db: Session = Depends(get_db)):
# #     order = db.query(Order).filter(Order.id == order_id).first()
# #     if order is None:
# #         raise HTTPException(status_code=404, detail="Order not found")
# #     return order

# # @app.get("/orders/{order_id}/items", response_model=List[OrderItem])
# # def get_order_items(order_id: int, db: Session = Depends(get_db)):
# #     order_items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
# #     if not order_items:
# #         raise HTTPException(status_code=404, detail="No items found for this order")
# #     return order_items

# # #  __________________________________________
# # # DELETE an order
# # @app.delete("/orders/{order_id}")
# # def delete_order(order_id: int, db: Session = Depends(get_db)):
# #     order = db.query(Order).filter(Order.id == order_id).first()
# #     if order is None:
# #         raise HTTPException(status_code=404, detail="Order not found")
    
# #     # Delete associated order items
# #     db.query(OrderItem).filter(OrderItem.order_id == order_id).delete()
# #     db.delete(order)
# #     db.commit()
    
# #     return {"detail": "Order and associated items deleted successfully"}
