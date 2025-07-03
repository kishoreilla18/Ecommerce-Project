from flask import Flask,request,render_template,redirect,url_for,flash,session,Response
import mysql.connector
from flask_session import Session
import bcrypt
from otp import genotp
from cmail import send_mail
from stoken import entoken,dtoken
import os
import razorpay
import re
import pdfkit

client = razorpay.Client(auth=("rzp_test_KV5IxD963ZGQVe","nHv2RIMoY6C0X6PDjfAkRoav"))
application=Flask(__name__)
# config=pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
application.config['SESSION_TYPE']='filesystem'
application.secret_key='kishore@07'
user=os.environ.get('RDS_USERNAME')
db=os.environ.get('RDS_DB_NAME')
password=os.environ.get('RDS_PASSWORD')
port=os.environ.get('RDS_PORT')
host=os.environ.get('RDS_HOSTNAME')
with mysql.connector.connect(user=user,post=port,db=db,password=password,host=host) as conn:
    cursor=conn.cursor()
    cursor.execute("CREATE TABLE if not exists admin_details (admin_username varchar(30) NOT NULL,admin_email varchar(50) NOT NULL,admin_password varbinary(255) DEFAULT NULL,created_at datetime DEFAULT CURRENT_TIMESTAMP,address text,PRIMARY KEY (admin_email),UNIQUE KEY admin_email (admin_email))")
    cursor.execute("CREATE TABLE if not exists items (itemid binary(16) NOT NULL,item_name mediumtext NOT NULL,description longtext NOT NULL,item_cost decimal(20,4) NOT NULL,item_quantity tinyint unsigned NOT NULL,item_category enum('Home appliances','Electronics','Sports','Fashion','Grocery') DEFAULT NULL,added_by varchar(50) DEFAULT NULL,created_at datetime DEFAULT CURRENT_TIMESTAMP,imgname varchar(20) DEFAULT NULL,PRIMARY KEY (itemid),KEY item_addedby (added_by),CONSTRAINT item_addedby FOREIGN KEY (added_by) REFERENCES admin_details (admin_email))")
    cursor.execute("CREATE TABLE if not exists users (useremail varchar(30) NOT NULL,username varchar(30) NOT NULL,password varchar(255) DEFAULT NULL,address text NOT NULL,created_at datetime DEFAULT CURRENT_TIMESTAMP,gender enum('Male','Female','Other') DEFAULT NULL,PRIMARY KEY (useremail))")
    cursor.execute("CREATE TABLE if not exists orders (order_id int unsigned NOT NULL AUTO_INCREMENT,order_date datetime DEFAULT CURRENT_TIMESTAMP,item_id binary(16) NOT NULL,item_name varchar(255) NOT NULL,total decimal(10,2) DEFAULT NULL,payment_by varchar(30) DEFAULT NULL,PRIMARY KEY (order_id),KEY payment_by (payment_by),KEY item_id (item_id),CONSTRAINT orders_ibfk_1 FOREIGN KEY (payment_by) REFERENCES users (useremail) ON DELETE SET NULL ON UPDATE CASCADE,CONSTRAINT orders_ibfk_2 FOREIGN KEY (item_id) REFERENCES items (itemid) ON UPDATE CASCADE)")
    cursor.execute("CREATE TABLE if not exists reviews (r_id int unsigned NOT NULL AUTO_INCREMENT,review_text text,created_at datetime DEFAULT CURRENT_TIMESTAMP,itemid binary(16) DEFAULT NULL,added_by varchar(30) DEFAULT NULL,rating enum('1','2','3','4','5') DEFAULT NULL,PRIMARY KEY (r_id),KEY itemid (itemid),KEY added_by (added_by),CONSTRAINT reviews_ibfk_1 FOREIGN KEY (itemid) REFERENCES items (itemid) ON DELETE SET NULL ON UPDATE CASCADE,CONSTRAINT reviews_ibfk_2 FOREIGN KEY (added_by) REFERENCES users (useremail) ON DELETE SET NULL ON UPDATE CASCADE)")
mydb=mysql.connector.connect(user=user,host=host,password=password,db=db,port=port)
Session(application)
# mydb=mysql.connector.connect(user='root',host='localhost',password='admin',db='ecommy')
@application.route('/')
def home():
    return render_template('welcome.html')

@application.route('/index')
def index():
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(itemid),item_name,description,item_cost,item_quantity,item_category,created_at,imgname from items')
        items_data=cursor.fetchall()
    except Exception as e:
        print(f'Error is:{e}')
        flash('Couldnot fetch the items')
        return redirect(url_for('index'))
    else:
        return render_template('index.html',items_data=items_data)

@application.route('/category/<ctype>')
def category(ctype):
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(itemid),item_name,description,item_cost,item_quantity,item_category,created_at,imgname from items where item_category=%s',[ctype])
        items_data=cursor.fetchall()
    except Exception as e:
        print(f'Error is:{e}')
        flash('Couldnot fetch the items')
        return redirect(url_for('index'))
    return render_template('dashboard.html',items_data=items_data)

@application.route('/admincreate',methods=['GET','POST'])
def admincreate():
    if request.method=='POST':
        username=request.form['username']
        useremail=request.form['email']
        password=request.form['password']
        address=request.form['address']
        agreed=request.form['agree']
        print(request.form)
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(admin_email) from admin_details where admin_email=%s',[useremail])
            email_count=cursor.fetchone() #(0,)
        except Exception as e:
            print(f'actual error is {e}')
            flash('Could not fetch the dta pls try again')
            return redirect(url_for('admincreate'))
        else:
            if email_count[0]==0:
                otp=genotp()
                admindata={'username':username,'useremail':useremail,'password':password,'address':address,'agreed':agreed,'otp':otp}
                subject='OTP for admin verrification'
                body=f'use the given otp for admin verify {otp}'
                send_mail(to=useremail,subject=subject,body=body)
                flash(f'otp has been sent to given email {useremail}')
                return redirect(url_for('otpverify',endata=entoken(data=admindata)))

            elif email_count[0]==1:
                flash(f'Email already existed {useremail}')
                return redirect(url_for('admincreate'))

    return render_template('admincreate.html')

@application.route('/otpverify/<endata>',methods=['GET','POST'])
def otpverify(endata):
    if request.method=='POST':
        uotp=request.form['otp']
        ddata=dtoken(data=endata)
        hashed=bcrypt.hashpw(ddata['password'].encode(),bcrypt.gensalt())
        print(hashed)
        print(type(hashed))
        if ddata['otp']==uotp:
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into admin_details(admin_username,admin_email,admin_password,address) values(%s,%s,%s,%s)',[ddata['username'],ddata['useremail'],hashed,ddata['address']])
                mydb.commit()
                cursor.close()
            except Exception as e:
                print(f'the error is {e}')
                flash('Unable to store data')
                return redirect(url_for('admincreate'))
            else:
                flash(f'Admin details successfully stored')
                return redirect(url_for('adminlogin'))
        else:
            flash(f'otp Wrong')

    return render_template('adminotp.html')

@application.route('/adminlogin',methods=['GET','POST'])
def adminlogin():
    if request.method=='POST':
        try:
            useremail=request.form['email']
            password=request.form['password'].encode()
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(admin_email) from admin_details where admin_email=%s',[useremail])
            count_email=cursor.fetchone() #(0,) (1,)
        except Exception as e:
            print(e)
            flash('Something went Wrong pls try again!')
            return redirect(url_for('adminlogin'))
        else:
            if count_email[0]==1:
                cursor.execute('select admin_password from admin_details where admin_email=%s',[useremail])
                stored_password=cursor.fetchone()[0] #('111',)
                print(password,stored_password)
                session['admin']=useremail
                if bcrypt.checkpw(password,stored_password):
                    return redirect(url_for('admindashboard'))
                else:
                    flash('password wrong')
                    return redirect(url_for('adminlogin'))
            elif count_email[0]==0:
                flash('Email not fount')
                return redirect(url_for('adminlogin'))
    return render_template('adminlogin.html')

@application.route('/admindashboard')
def admindashboard():
    return render_template('adminpanel.html')

@application.route('/additem',methods=['GET','POST'])
def additem():
    if request.method=='POST':
        item_name=request.form['title']
        item_desc=request.form['Discription']
        item_quantity=request.form['quantity']
        item_cost=request.form['price']
        item_category=request.form['category']
        item_image=request.files['file']
        print(request.form)
        filename=genotp()+'.'+item_image.filename.split('.')[-1]
        print('filename: ',filename)
        try:
            path=os.path.abspath(__file__)
            print(path)
            dname=os.path.dirname(path)
            print(dname)
            static_path=os.path.join(dname,'static')
            print(static_path)
            item_image.save(os.path.join(static_path,filename))
            cursor=mydb.cursor(buffered=True)
            cursor.execute('insert into items(itemid,item_name,description,item_cost,item_quantity,item_category,added_by,imgname) values(uuid_to_bin(uuid()),%s,%s,%s,%s,%s,%s,%s)',[item_name,item_desc,item_cost,item_quantity,item_category,session.get('admin'),filename])
            print('success')
            mydb.commit()
            cursor.close()
        except Exception as e:
            print(f'the error is {e}')
            return redirect(url_for('additem'))
        else:
            flash(f'{item_name[:20]}. add sucessfully')
            return redirect(url_for('additem'))

    return render_template('additem.html')
@application.route('/viewitems')
def viewitems():
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select bin_to_uuid(itemid),item_name,item_cost,imgname from items where added_by=%s',[session.get('admin')])
            itemsdata=cursor.fetchall()
            print(itemsdata)
        except Exception as e:
            print(f'the error is {e}')
            flash('Could not fetch the data')
            return redirect(url_for('admindashboard'))
        else:
            return render_template('viewall_items.html',itemsdata=itemsdata)
    else:
        flash(f'pls login first')
        return redirect(url_for('adminlogin'))

@application.route('/viewitem/<itemid>')
def viewitem(itemid):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select *from items where itemid=uuid_to_bin(%s) and added_by=%s',[itemid,session.get('admin')])
    itemdata=cursor.fetchone()
    print(itemdata)
    return render_template('view_item.html',itemdata=itemdata)

@application.route('/updateitem/<itemid>',methods=['GET','POST'])
def updateitem(itemid):
      if session.get('admin'):
        try:
            cursor=mydb.cursor()
            cursor.execute('select bin_to_uuid(itemid),item_name, description ,item_cost,item_quantity,item_category,imgname,created_at  from items where itemid=uuid_to_bin(%s) and added_by=%s',[itemid,session.get('admin')])
            itemsdata=cursor.fetchone()
        except Exception as e:
            print(f"the error is{e}")
            flash('could not fetch the data')
            return redirect(url_for('viewitems'))
        else:
            if request.method=='POST':
                item_name=request.form['title']
                item_desc=request.form['Discription']
                item_quantity=request.form['quantity']
                item_cost=request.form['price']
                item_category=request.form['category']
                item_image=request.files['file']
                if item_image.filename=='':
                    filename=itemsdata[6]
                else:
                    filename=genotp()+'.'+item_image.filename.split('.')[-1]
                    path=os.path.abspath(__file__)
                    dname=os.path.dirname(path)
                    static_path=os.path.join(dname,'static')
                    item_image.save(os.path.join(static_path,filename))
                    os.remove(os.path.join(static_path,itemsdata[6]))
                cursor=mydb.cursor()
                cursor.execute('update items set item_name=%s, description=%s, item_cost=%s, item_quantity=%s, item_category=%s, imgname=%s where itemid=uuid_to_bin(%s) and added_by=%s',[item_name,item_desc,item_cost,item_quantity,item_category,filename,itemid,session.get('admin')])
                mydb.commit()
                cursor.close()
                

    
                return redirect(url_for('viewitems', itemid=itemid))
            

                 
            return render_template('update_item.html',item_data=itemsdata)
        
@application.route('/deleteitem/<itemid>')
def deleteitem(itemid):
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select imgname from items where itemid=uuid_to_bin(%s) and added_by=%s',[itemid,session.get('admin')])
        stored_imgname=cursor.fetchone()[0]
        path=os.path.abspath(__file__)
        dname=os.path.dirname(path)
        static_path=os.path.join(dname,'static')
        os.remove(os.path.join(static_path, stored_imgname))
        cursor.execute('delete from items where itemid=uuid_to_bin(%s) and added_by=%s',[itemid,session.get('admin')])
        mydb.commit()
        cursor.close()
    except Exception as e:
        print(f'the error is {e}')
        flash(f'item could not delete')
        return redirect(url_for('viewitems'))
    else:
        flash('item deleted successfuly')
        return redirect(url_for('viewitems'))



@application.route('/usersignup',methods=['GET','POST'])
def usersignup():
    if request.method=="POST":
        username=request.form['name']
        useremail=request.form['email']
        address=request.form['address']
        password=request.form['password']
        usergender=request.form['usergender']
        print(request.form)
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(useremail) from users where useremail=%s',[useremail])
            email_count=cursor.fetchone()
        except Exception as e:
            print(f'the error is {e}')
            flash('could not fetch the data, plz Try again!')
            return redirect(url_for('usersignup'))
        else:
            if email_count[0]==0:
                otp=genotp()
                userdata={'username':username,'useremail':useremail,'password':password,'address':address,'usergender':usergender,'otp':otp}
                subject='OTP for User verification'
                body=f'use the given otp for user verify {otp}'
                send_mail(to=useremail,subject=subject,body=body)
                flash(f'otp has been sent to given email {useremail}')
                return redirect(url_for('userotpverify',endata=entoken(data=userdata)))

            elif email_count[0]==1:
                flash(f'Email already existed {useremail}')
                return redirect(url_for('usersignup'))

    return render_template('usersignup.html')

@application.route('/userotpverify/<endata>',methods=['GET','POST'])
def userotpverify(endata):
    if request.method=='POST':
        uotp=request.form['otp']
        ddata=dtoken(data=endata)
        hashed=bcrypt.hashpw(ddata['password'].encode(),bcrypt.gensalt())
        print(hashed)
        print(type(hashed))
        if ddata['otp']==uotp:
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into users(username,useremail,password,address,gender) values(%s,%s,%s,%s,%s)',[ddata['username'],ddata['useremail'],hashed,ddata['address'],ddata['usergender']])
                mydb.commit()
                cursor.close()
            except Exception as e:
                print(f'the error is {e}')
                flash('Unable to store data')
                return redirect(url_for('usersignup'))
            else:
                flash(f'User details successfully stored')
                return redirect(url_for('userlogin'))
        else:
            flash(f'otp Wrong')

    return render_template('userotp.html')

@application.route('/userlogin',methods=['GET','POST'])
def userlogin():
    if request.method=='POST':
        try:
            useremail=request.form['email']
            password=request.form['password'].encode()
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(useremail) from users where useremail=%s',[useremail])
            count_email=cursor.fetchone()
        except Exception as e:
            print(f'the error is {e}')
            flash('Something went Wrong! plz try again...')
            return redirect(url_for('userlogin'))
        else:
            if count_email[0]==1:
                cursor.execute('select password from users where useremail=%s',[useremail])
                stored_password=cursor.fetchone()[0].encode()
                print(password,stored_password)
                if bcrypt.checkpw(password,stored_password):
                    session['user']=useremail
                    if not session.get(useremail):
                        session[useremail]={}
                    return redirect(url_for('index'))
                else:
                    flash('password Wrong')
                    return redirect(url_for('userlogin'))
            elif count_email[0]==0:
                flash('Email Not found!')
                return redirect(url_for('userlogin'))
    return render_template('userlogin.html')


@application.route('/adminlogout')
def adminlogout():
    if session.get('admin'):
        session.pop('admin')
        return redirect(url_for('index'))
    else:
        flash('For logout Pls login')
        return redirect(url_for('adminlogin'))
    
@application.route('/userlogout')
def userlogout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('index'))
    else:
        flash('For logout Pls login')
        return redirect(url_for('userlogin'))

@application.route('/addcart/<itemid>/<name>/<price>/<category>/<img>')
def addcart(itemid,name,price,category,img):
    if session.get('user'):
        if itemid not in session[session.get('user')]:
            session[session.get('user')][itemid]=[name,price,1,img,category] #adding cart item using session data
            session.modify=True
            flash(f'{name[0:10]} item item added to cart')
            return redirect(url_for('index'))
        else:
            session[session.get('user')][itemid][2]+=1 #if item already in cart increment the quantity
            session.modify=True
            flash(f'item already in cart')
            print('item already in cart')
            return redirect(url_for('index'))
    else:
        return redirect(url_for('userlogin'))
    
@application.route('/viewcart')
def viewcart():
    if session.get('user'):
        items=session[session.get('user')]
        if items:
            return render_template('cart.html',items=items)
        else:
            flash('No items in cart')
            return redirect(url_for('index'))
    else:
        flash('pls login first')
        return redirect(url_for('userlogin'))

@application.route('/removecart/<itemid>')
def removecart(itemid):
    if session.get('user'):
        if session[session.get('user')]:
            session[session.get('user')].pop(itemid)
            session.modify=True
            flash(f'{itemid} removed from cart')
            return redirect(url_for('viewcart'))
        else:
            flash(f'item unable to remove')
            return redirect(url_for('viewcart'))
    else:
        flash('pls login first')

@application.route('/pay/<itemid>/<name>/<float:price>/<quantity>',methods=['GET','POST'])
def pay(itemid,name,price,quantity):
    if session.get('user'):
        try:
            if request.method=='POST':
                qyt=int(request.form['qyt'])
            else:
                qyt=int(quantity)
            price=price*100
            amount=price*qyt
            print(amount,qyt)
            print(f'creating payment for item:{itemid}, name :{name}, price:{amount}')
            order=client.order.create({
                "amount": amount,
                "currency": "INR",
                "payment_capture":'1' })
            print(f'order created: {order}')
            return render_template('pay.html',order=order,itemid=itemid,name=name,total_amount=amount)
        except Exception as e:
            print(f'could not place order {e}')
            return redirect(url_for('viewcart'))

    else:
        flash('pls login first')
        return redirect(url_for('userlogin'))

@application.route('/success',methods=['GET','POST'])
def success():
    if request.method=='POST':
        payment_id=request.form['razorpay_payment_id']
        order_id=request.form['razorpay_order_id']
        order_signature=request.form['razorpay_signature']
        itemid=request.form['itemid']
        name=request.form['name']
        total_amount=request.form['total_amount']
        params_dict={
            'razorpay_payment_id':payment_id,
            'razorpay_order_id':order_id,
            'razorpay_signature':order_signature
        }
        try:
            client.utility.verify_payment_signature(params_dict)
        except razorpay.error.SignatureVerificationError:
            return 'Payment verification failed',400
        else:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('insert into orders(item_id,item_name,total,payment_by) values(uuid_to_bin(%s),%s,%s,%s)',[itemid,name,total_amount,session.get('user')])
            mydb.commit()
            flash(f'order placed with {total_amount}')
            orderdetails={'itemname':name,'useremail':session.get('user'),'payment_id':payment_id,'order_id':order_id,'itemid':itemid,'amount':total_amount}
            subject=f'Order Confirmed {name}'
            body=f'''Dear Customer,

            Thank you for your order! Your order has been placed successfully.

            Here are your order details:

            Item Name     : {name}
            Order ID      : {order_id}
            Payment ID    : {payment_id}
            Amount Paid   : ₹{total_amount}
            Registered Email: {session.get('user')}'''
            send_mail(to=session.get('user'),subject=subject,body=body)
            return redirect(url_for('index'))

@application.route('/orders')
def orders():
    if session.get('user'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select *from orders where payment_by=%s',[session.get('user')])
            user_orders=cursor.fetchall()
            print(user_orders)
        except Exception as e:
            print(f'{e}')
            flash('coul;d not fetch orders')
            return redirect(url_for('index'))
        else:
            return render_template('orders.html',user_orders=user_orders)
    else:
        flash('[pls login first]')
        return redirect(url_for('userlogin'))

@application.route('/description/<itemid>')
def description(itemid):
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(itemid),item_name,description,item_cost,item_quantity,item_category,imgname,created_at from items where itemid=uuid_to_bin(%s)',[itemid])
        itemdata=cursor.fetchone() #(1,'apple','fvhfbf',345,789,'grocery','apple.jpg','2025-09-23')
    except Exception as e:
        print(f'Error:{e}')
        flash('Could not fetch details')
        return redirect(url_for('index'))
    else:
        return render_template('description.html',itemdata=itemdata)

@application.route('/addreview/<itemid>',methods=['GET','POST'])
def addreview(itemid):
    if session.get('user'):
        if request.method=='POST':
            review=request.form['review']
            rating=request.form['rate']
            cursor=mydb.cursor(buffered=True)
            cursor.execute('insert into reviews(review_text,rating,itemid,added_by) values(%s,%s,uuid_to_bin(%s),%s)',[review,rating,itemid,session.get('user')])
            mydb.commit()
            flash('review added successfully')
            return redirect(url_for('description',itemid=itemid))
        return render_template('review.html')
    else:
        flash('pls login to add review')
        return redirect(url_for('description',itemid=itemid))

@application.route('/readreview/<itemid>')
def readreview(itemid):
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select added_by,review_text,rating,created_at from reviews where itemid=uuid_to_bin(%s)',[itemid])
        reviewdata=cursor.fetchall()
        print(reviewdata)
        cursor.execute('select bin_to_uuid(itemid),item_name,description,item_cost,item_quantity,item_category,imgname,created_at from items where itemid=uuid_to_bin(%s)',[itemid])
        itemdata=cursor.fetchone()
    except Exception as e:
        flash(f'the error is {e}')
    else:
        return render_template('readreview.html',reviewdata=reviewdata,item_data=itemdata)

@application.route('/search',methods=['GET','POST'])
def search():
    if request.method=='POST':
        search_data=request.form['search']
        string=['A-Za-z0-9']
        pattern=re.compile(f'^{string}',re.IGNORECASE)
        if (pattern.match(search_data)):
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select bin_to_uuid(itemid),item_name,description,item_cost,item_quantity,item_category,created_at,imgname from items where itemid like %s or item_name like %s or description like %s or item_category like %s',[search_data+'%',search_data+'%',search_data+'%',search_data+'%'])
                matcheddata=cursor.fetchall()
            except Exception as e:
                print(f'error is {e}')
                flash(f'could not fetch search data')
            else:
                print(matcheddata)
                return render_template('dashboard.html',items_data=matcheddata)
        else:
            flash('No data give')
            return redirect(url_for('index'))

'''
@application.route('/getinvoice/<ordid>.pdf')
def getinvoice(ordid):
    if session.get('user'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select * from orders where order_id=%s and payment_by=%s',[ordid,session.get('user')])
            order_data=cursor.fetchone()
            cursor.execute('select useremail,username,address,gender from users where useremail=%s',[session.get('user')])
            user_data=cursor.fetchone()
            html=render_template('bill.html',order_data=order_data,user_data=user_data)
            pdf=pdfkit.from_string(html,False,configuration=config)
            response=Response(pdf,content_type='application/pdf')
            response.headers['Content-Dispoition']='inline; filename=output.pdf'
            return response
        except Exception as e:
            print(f'error is {e}')
            flash('could not convert pdf')
            return redirect(url_for('orders'))
    else:
        flash('Pls login first')
        return redirect(url_for('userlogin'))'''

@application.route('/forgotpassword',methods=('GET','POST'))
def forgotpassword():
        if request.method=='POST':
            f_email=request.form['email']
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(*) from users where useremail=%s',[f_email])
            count_email=cursor.fetchone()
            if count_email[0]==1:
                subject=f'Reset link for SNM website forgot password'
                body=f"click to reset link: {url_for('newpassword',data=entoken(f_email),_external=True)}"
                send_mail(to=f_email,subject=subject,body=body)
                flash(f'Reset link has been set to given mailID {f_email}')
                return redirect(url_for('userlogin'))
            elif count_email[0]==0:
                flash(f'Please register your account')
                return redirect(url_for('usersignup'))
                
        return render_template('forgotpassword.html')

@application.route('/newpassword/<data>',methods=['GET','POST'])
def newpassword(data):
        if request.method=='POST':
            npassword=request.form['new_password']
            cpassword=request.form['confirm_password']
            if npassword==cpassword:
                email=dtoken(data)
                hashed=bcrypt.hashpw(cpassword.encode(),bcrypt.gensalt())
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update users set password=%s where useremail=%s',[hashed,email])
                mydb.commit()
                flash(f'newpassword updated successfully Please login')
                return redirect(url_for('userlogin'))
            else:
                flash('Mismatched password Please check')
                return redirect(url_for('newpassword',data=data))
        return render_template('newpassword.html')

if __name__=='__main__':
    application.run()