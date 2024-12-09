from http.client import HTTPResponse
import os
from xml.dom.expatbuilder import FragmentBuilder
from flask import flash, redirect, render_template, request, url_for, session
from pyparsing import nums
from market import app, db, bcrypt
import random
from datetime import datetime,date
from functools import wraps
from markupsafe import escape
from market.forms import AddProductForm, CustomerRegistrationForm, AdminRegistrationForm, SellerRegistrationForm, LoginForm, PromoOfferForm, PromoCodeForm
from werkzeug.utils import secure_filename

cart_id=0
total_val=0.0
total_count=0.0
customer_cart_list=[]

UPLOAD_FOLDER = 'market/static/uploads' 
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def auth_required(role=None):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if the user is logged in
            if 'user_id' not in session:
                flash('You need to log in first.')
                return render_template('homepage.html')

            # Check the user's role
            if role and session.get('user_type') != role:
                flash('You do not have permission to access this page.')
                return render_template('homepage.html')

            # Check if the user_id in session matches any of the expected IDs in kwargs
            if ('user_id' in kwargs and session['user_id'] != int(kwargs['user_id'])) or \
               ('seller_id' in kwargs and session['user_id'] != int(kwargs['seller_id'])) or \
               ('admin_id' in kwargs and session['user_id'] != int(kwargs['admin_id'])):
                flash('Unauthorized access. Please log in to continue!')
                return render_template('homepage.html')

            return f(*args, **kwargs)
        return decorated_function
    return wrapper

# SQLAlchemy Models 
class Customer(db.Model):
    __tablename__ = 'customer'
    Customer_ID = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    email = db.Column(db.String(100), unique=True)
    mobile_no = db.Column(db.String(20))
    password = db.Column(db.String(80))

class Admin(db.Model):
    __tablename__ = 'admin'
    Admin_ID = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    password = db.Column(db.String(80))

class Seller(db.Model):
    __tablename__ = 'seller'
    Seller_ID = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    email = db.Column(db.String(100), unique=True)
    phone_number = db.Column(db.String(20))
    password = db.Column(db.String(80))
    place_of_operation = db.Column(db.String(100))
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.Admin_ID'))

class Order(db.Model):
    __tablename__ = 'orders'
    Order_ID = db.Column(db.Integer, primary_key=True)
    mode = db.Column(db.String(50))
    amount = db.Column(db.Float)
    date = db.Column(db.Date)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.Customer_ID'))

class Offer(db.Model):
    __tablename__ = 'offer'
    Offer_ID = db.Column(db.Integer, primary_key=True)
    promo_code = db.Column(db.String(50), unique=True)
    percentage_discount = db.Column(db.Float)
    min_order_value = db.Column(db.Float)
    max_discount = db.Column(db.Float)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.Admin_ID'))

class DeliveryBoy(db.Model):
    __tablename__ = 'delivery_boy'
    Delivery_Boy_ID = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    mobile_no = db.Column(db.String(20))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(80))
    average_rating = db.Column(db.Float, default=None)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.Admin_ID'))

class Product(db.Model):
    __tablename__ = 'product'
    Product_ID = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.Float)
    brand = db.Column(db.String(100))
    measurement = db.Column(db.String(100))
    category_id = db.Column(db.Integer)
    unit = db.Column(db.String(50))
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.Admin_ID'))
    image = db.Column(db.String(120))

class Cart(db.Model):
    __tablename__ = 'cart'
    Cart_ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Total_Value = db.Column(db.Float, nullable=False)
    Total_Count = db.Column(db.Integer, nullable=False)
    Offer_ID = db.Column(db.Integer, nullable=True)
    Final_Amount = db.Column(db.Float, nullable=False)

class AssociatedWith(db.Model):
    __tablename__ = 'associated_with'
    id = db.Column(db.Integer, primary_key=True)
    Customer_ID = db.Column(db.Integer, db.ForeignKey('customer.Customer_ID'))
    Cart_ID = db.Column(db.Integer, db.ForeignKey('cart.Cart_ID'))
    Product_ID = db.Column(db.Integer, db.ForeignKey('product.Product_ID'))

class Sells(db.Model):
    __tablename__ = 'sells'
    id = db.Column(db.Integer, primary_key=True)
    Seller_ID = db.Column(db.Integer, db.ForeignKey('seller.Seller_ID'))
    Product_ID = db.Column(db.Integer, db.ForeignKey('product.Product_ID'))
    No_of_Product_Sold = db.Column(db.Integer)

@app.route('/admin/<admin_id>')
@auth_required('admin')
def adminRedirect(admin_id):
    return render_template('adminOption.html', admin_id=admin_id)

@app.route('/adminOrder/<admin_id>', methods=['GET', 'POST'])
@auth_required('admin')
def adminViewOrder(admin_id):
    my_list = []
    order_all = Order.query.all()
    for order in order_all:
        temp_dict = {
            'Order_ID': order.Order_ID,
            'Mode': order.mode,
            'Amount': order.amount,
            'Date': order.date
        }
        my_list.append(temp_dict)
    if request.method == 'POST':
        return redirect('/admin/' + str(admin_id))
    return render_template('viewOrder.html', list=my_list)

@app.route('/adminOffer/<admin_id>', methods=['GET', 'POST'])
@auth_required('admin')
def adminAddOffer(admin_id):
    form = PromoOfferForm()
    if form.validate_on_submit():
        promo_code = form.promo_code.data
        percentage_discount = form.percentage_discount.data
        min_order_value = form.min_order_value.data
        max_discount = form.max_discount.data
        new_offer = Offer(
            promo_code=promo_code,
            percentage_discount=percentage_discount,
            min_order_value=min_order_value,
            max_discount=max_discount,
            admin_id=admin_id
        )
        db.session.add(new_offer)
        db.session.commit()
        flash('You have successfully added an Offer!')
        return redirect(url_for('adminAddOffer', admin_id=admin_id))
    return render_template('addOffer.html', admin_id=admin_id, form=form)

@app.route('/adminDelivery_boy/<admin_id>', methods=['GET', 'POST'])
@auth_required('admin')
def adminAdd_Delivery_Boy(admin_id):
    if request.method == 'POST':
        delivery_boy_Details = request.form
        first_name = delivery_boy_Details['First_Name']
        last_name = delivery_boy_Details['Last_Name']
        mobile_no = delivery_boy_Details['Mobile_No']
        email = delivery_boy_Details['Email']
        password = delivery_boy_Details['Password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_delivery_boy = DeliveryBoy(
            first_name=first_name,
            last_name=last_name,
            mobile_no=mobile_no,
            email=email,
            password=hashed_password,
            admin_id=admin_id
        )
        db.session.add(new_delivery_boy)
        db.session.commit()
        flash('You have successfully added a delivery boy!')
    return render_template('addDelivery.html', admin_id=admin_id)

@app.route('/adminSeller/<admin_id>', methods=['GET', 'POST'])
@auth_required('admin')
def adminAdd_Seller(admin_id):
    if request.method == 'POST':
        Seller_Details = request.form
        first_name = Seller_Details['First_Name']
        last_name = Seller_Details['Last_Name']
        email = Seller_Details['Email']
        phone_number = Seller_Details['Phone_Number']
        password = Seller_Details['Password']
        place_of_operation = Seller_Details['Place_Of_Operation']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_seller = Seller(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number,
            password=hashed_password,
            place_of_operation=place_of_operation,
            admin_id=admin_id
        )
        db.session.add(new_seller)
        db.session.commit()
        flash('You have successfully added a seller!')
    return render_template('addSeller.html', admin_id=admin_id)

@app.route('/adminProduct/<admin_id>', methods=['GET', 'POST'])
@auth_required('admin')
def adminAdd_Product(admin_id):
    form = AddProductForm()
    if form.validate_on_submit():

        # Save the uploaded image 
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        image_file = form.image.data 
        filename = secure_filename(image_file.filename) 
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename) 
        image_file.save(image_path)
        
        # Create a new product object
        new_product = Product(
        name=form.name.data,
        price=form.price.data,
        brand=form.brand.data,
        measurement=form.measurement.data,
        category_id=form.category_id.data,
        unit=form.unit.data,
        admin_id=admin_id,
        image=filename
        )
            
        # Add to the session and commit to the database
        db.session.add(new_product)
        db.session.commit()
        flash('You have successfully added a Product!', 'success')
        return redirect(url_for('adminAdd_Product', admin_id=admin_id))
    return render_template('addNewProducts.html', admin_id=admin_id, form=form)

@app.route('/sell/<seller_id>', methods=['GET', 'POST'])
@auth_required('seller')
def sell(seller_id):
    if request.method == 'POST':
        ProdDetail = request.form
        name = ProdDetail['Name']
        brand = ProdDetail['Brand']
        quantity = ProdDetail['Quantity']
        product = Product.query.filter_by(name=name, brand=brand).first()
        if not product or int(quantity) < 0:
            flash('Invalid Product details or Quantity')
        else:
            new_sale = Sells(Seller_ID=seller_id, Product_ID=product.Product_ID, No_of_Product_Sold=quantity)
            db.session.add(new_sale)
            db.session.commit()
            flash('Product added successfully')
    return render_template('addProduct.html')

def reinitialize():
    global cart_id
    global total_count
    global total_val
    global customer_cart_list
    cart_id = StaticClass.giveCartId()
    total_val=0.0
    total_count=0.0
    customer_cart_list=[]

@app.route('/home/<user_id>', methods=['GET', 'POST'])
@auth_required('customer')
def userEnter(user_id):
    my_list = []
    global cart_id, total_count, total_val, customer_cart_list
    products = Product.query.all()
    for prod in products:
        temp_dict = {
            'Name': prod.name,
            'Price': prod.price,
            'Brand': prod.brand,
            'Image': prod.image or 'default.png'  # Use 'default.png' if no image is uploaded
        }
        my_list.append(temp_dict)
    if request.method == 'POST':
        new_cart = Cart(Cart_ID=cart_id, Total_Value=total_val, Total_Count=total_count, Offer_ID=3, Final_Amount=total_val)
        db.session.add(new_cart)
        db.session.commit()
        print("hi")
        return redirect(url_for('placeOrder', user_id=user_id))
    else:
        purchaseDetails = request.args
        if 'Name' in purchaseDetails and 'Brand' in purchaseDetails and 'Price' in purchaseDetails:
            try:
                name = purchaseDetails['Name']
                brand = purchaseDetails['Brand']
                price = purchaseDetails['Price']
                total_count += 1
                total_val += float(price)
                temp_dict = {'Name': name, 'Brand': brand, 'Price': price}
                customer_cart_list.append(temp_dict)
                flash('Product has been added successfully to the cart!')
            except KeyError:
                flash("Error: KeyError")

    return render_template('home.html', list=my_list)


@app.route('/order/<user_id>', methods=['GET', 'POST'])
@auth_required('customer')
def placeOrder(user_id):
    global customer_cart_list, cart_id, total_val
    form = PromoCodeForm()  # Create an instance of the form
    print(form.csrf_token.data)
    if form.validate_on_submit():
        p_code = form.promo_code.data
        offer = Offer.query.filter_by(promo_code=p_code).first()
        if not offer or p_code == 'Coupon_Code':
            new_cart_offer = Cart.query.filter_by(Cart_ID=cart_id).first()
            new_cart_offer.Offer_ID = None
            db.session.commit()
        else:
            if total_val > offer.min_order_value:
                dval = (total_val * offer.percentage_discount) / 100
                deduct = min(dval, offer.max_discount)
                total_val -= deduct
                new_cart_offer = Cart.query.filter_by(Cart_ID=cart_id).first()
                new_cart_offer.Offer_ID = offer.Offer_ID
                new_cart_offer.Final_Amount = total_val
                db.session.commit()
        for item in customer_cart_list:
            product = Product.query.filter_by(name=item['Name']).first()
            if product:
                new_association = AssociatedWith(Customer_ID=user_id, Cart_ID=cart_id, Product_ID=product.Product_ID)
                db.session.add(new_association)
                db.session.commit()
        return redirect(url_for('order_placing', user_id=user_id))
    return render_template('order.html', list=customer_cart_list, form=form)  # Pass the form to the template

@app.route('/HomePage')
@app.route('/')
def homePage():
    return render_template('homepage.html')

@app.route('/loginRegisterSeller')
def loginRegisterSeller():
    return render_template('loginregisterSeller.html')

@app.route('/loginRegisterUser')
def loginRegisterUser():
    return render_template('loginregisterUser.html')

@app.route('/loginRegisterAdmin')
def loginRegisterAdmin():
    return render_template('loginregisterAdmin.html')

@app.route('/placeOrder/<user_id>', methods=['GET', 'POST'])
@auth_required('customer')
def order_placing(user_id):
    global total_val
    if request.method == 'POST':
        orderDetails = request.form
        hno = orderDetails['HNO']
        city = orderDetails['City']
        state = orderDetails['State']
        pincode = orderDetails['Pincode']
        mode = orderDetails['Mode']
        curr_date = date.today()
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        delivery_boy_ids = [boy.Delivery_Boy_ID for boy in DeliveryBoy.query.all()]
        delivery_boy_id = random.choice(delivery_boy_ids) if delivery_boy_ids else None
        new_order = Order(
            mode=mode,
            amount=total_val,
            city=city,
            state=state,
            date=curr_date,
            house_flat_no=hno,
            pincode=pincode,
            cart_id=cart_id,
            delivery_boy_id=delivery_boy_id,
            order_time=current_time
        )
        db.session.add(new_order)
        db.session.commit()
        flash('Your Order has been placed Successfully!')
    return render_template('orderDetails.html', total_val=total_val)

@app.route('/customerRegister', methods=['GET', 'POST'])
def customerRegister():
    form = CustomerRegistrationForm()
    if form.validate_on_submit():
        first_name = escape(form.first_name.data)
        last_name = escape(form.last_name.data)
        email = escape(form.email.data)
        mobile_no = escape(form.mobile_no.data)
        password = form.password.data
        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        # Create a new customer
        new_customer = Customer(
            first_name=first_name,
            last_name=last_name,
            email=email,
            mobile_no=mobile_no,
            password=hashed_password
        )
        # Add the new customer to the session and commit to the database
        db.session.add(new_customer)
        db.session.commit()
        flash('You have registered successfully!')
        return redirect(url_for('UserLogin'))
    return render_template('customerRegister.html', form=form)

@app.route('/adminRegister', methods=['GET', 'POST'])
def adminRegister():
    form = AdminRegistrationForm()
    if form.validate_on_submit():
        first_name = escape(form.first_name.data)
        last_name = escape(form.last_name.data)
        password = form.password.data
        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        # Create a new admin
        new_admin = Admin(
            first_name=first_name,
            last_name=last_name,
            password=hashed_password
        )
        # Add the new admin to the session and commit to the database
        db.session.add(new_admin)
        db.session.commit()
        flash('You have registered successfully!')
        return redirect(url_for('AdminLogin'))
    return render_template('adminRegister.html', form=form)

@app.route('/sellerRegister', methods=['GET', 'POST'])
def sellerRegister():
    form = SellerRegistrationForm()
    if form.validate_on_submit():
        first_name = escape(form.first_name.data)
        last_name = escape(form.last_name.data)
        email = escape(form.email.data)
        password = form.password.data
        phone_number = escape(form.phone_number.data)
        place_of_operation = escape(form.place_of_operation.data)
        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        # Select a random admin ID
        rand_admin = db.session.execute('SELECT Admin_ID FROM admin').fetchall()
        admin_id = random.choice(rand_admin)[0] if rand_admin else None
        # Create a new seller
        new_seller = Seller(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number,
            password=hashed_password,
            place_of_operation=place_of_operation,
            admin_id=admin_id
        )
        # Add the new seller to the session and commit to the database
        db.session.add(new_seller)
        db.session.commit()
        flash('You have registered successfully!')
        return redirect(url_for('SellerLogin'))
    return render_template('sellerRegister.html', form=form)

@app.route('/UserLogin', methods=['GET', 'POST'])
def UserLogin():
    form = LoginForm()
    if form.validate_on_submit():
        email = escape(form.email.data)
        password = form.password.data
        # Fetch the user by email
        customer = Customer.query.filter_by(email=email).first()
        if customer and bcrypt.check_password_hash(customer.password, password):
            session['user_id'] = customer.Customer_ID
            session['user_type'] = 'customer'
            session.permanent = True
            reinitialize()
            url_direct = '/home/' + str(customer.Customer_ID)
            return redirect(url_direct)
        else:
            flash('Invalid Email or Password')
    return render_template('UserLogin.html', form=form)

from market.forms import CustomerRegistrationForm, AdminRegistrationForm, SellerRegistrationForm, LoginForm, AdminLoginForm

@app.route('/AdminLogin', methods=['GET', 'POST'])
def AdminLogin():
    form = AdminLoginForm()
    if form.validate_on_submit():
        first_name = escape(form.first_name.data)
        last_name = escape(form.last_name.data)
        password = form.password.data
        # Fetch the admin by name
        admin = Admin.query.filter_by(first_name=first_name, last_name=last_name).first()
        if admin and bcrypt.check_password_hash(admin.password, password):
            session['user_id'] = admin.Admin_ID
            session['user_type'] = 'admin'
            session.permanent = True
            url_direct = '/admin/' + str(admin.Admin_ID)
            return redirect(url_direct)
        else:
            flash('Invalid Name or Password')
    return render_template('AdminLogin.html', form=form)

@app.route('/SellerLogin', methods=['GET', 'POST'])
def SellerLogin():
    form = LoginForm()
    if form.validate_on_submit():
        email = escape(form.email.data)
        password = form.password.data
        # Fetch the seller by email
        seller = Seller.query.filter_by(email=email).first()
        if seller and bcrypt.check_password_hash(seller.password, password):
            session['user_id'] = seller.Seller_ID
            session['user_type'] = 'seller'
            session.permanent = True
            url_direct = '/sell/' + str(seller.Seller_ID)
            return redirect(url_direct)
        else:
            flash('Invalid Email or Password')
    return render_template('SellerLogin.html', form=form)

class StaticClass:
    
    cart_id = random.randint(1000,100000)

    @staticmethod
    def giveCartId():
        StaticClass.cart_id +=1
        return StaticClass.cart_id