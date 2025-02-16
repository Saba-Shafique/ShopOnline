from sqlalchemy import Column, Integer, String, ForeignKey, Float, Table
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    cart_id = Column(Integer, ForeignKey('cart.id'))
    cart = relationship("Cart", back_populates="user", uselist=False)
    orders = relationship("Order", back_populates="user")

class Cart(Base):
    __tablename__ = 'cart'

    id = Column(Integer, primary_key=True, index=True)
    total_price = Column(Float, default=0.0)
    user = relationship("User", back_populates="cart", uselist=False)
    items = relationship("CartItem", back_populates="cart")

class Product(Base):
    __tablename__ = 'product'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String, index=True)  # New category field
    image = Column(String)  # Stores the path to the image file
    price = Column(Float)

    def __repr__(self):
        return f"<Product(name={self.name}, price={self.price})>"

class CartItem(Base):
    __tablename__ = 'cart_item'

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey('cart.id'))
    product_id = Column(Integer, ForeignKey('product.id'))
    quantity = Column(Integer, default=1)
    price = Column(Float)
    total_price = Column(Float)
    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")

# class Order(Base):
#     __tablename__ = 'order'

#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(Integer, ForeignKey('user.id'))
#     user = relationship("User")
#     total_amount = Column(Float)  # Total order amount
#     order_items = relationship("OrderItem", back_populates="order")

# class OrderItem(Base):
#     __tablename__ = 'order_item'

#     id = Column(Integer, primary_key=True, index=True)
#     order_id = Column(Integer, ForeignKey('order.id'))
#     product_id = Column(Integer, ForeignKey('product.id'))
#     quantity = Column(Integer)
#     price = Column(Float)
#     total_price = Column(Float)
#     order = relationship("Order", back_populates="order_items")
#     product = relationship("Product")

class Order(Base):
    __tablename__ = 'order'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    total_price = Column(Float, default=0.0)
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = 'order_item'

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('order.id'))
    product_id = Column(Integer, ForeignKey('product.id'))
    quantity = Column(Integer, default=1)
    price = Column(Float)
    total_price = Column(Float)
    order = relationship("Order", back_populates="items")
    product = relationship("Product")