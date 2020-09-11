from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators,ValidationError
from passlib.hash import sha256_crypt
from functools import wraps

# KULLANICI KAYIT FORMU
class RegisterForm(Form):
    name = StringField("İsim Soyisim",validators=[validators.Length(min=4,max=25)])
    username = StringField("Kullanıcı Adı",validators=[validators.Length(min=4,max=25)])
    email = StringField("E-Posta Adresi",validators=[validators.Email(message="Lütfen Geçerli Bir E-Posta girin")])
    password = PasswordField("Parola",validators=[
        validators.DataRequired(message="Lütfen Bir Parola Belirleyin"),
        validators.EqualTo(fieldname="confirm",message="Parolanız Uyuşmuyor")
    ])
    confirm = PasswordField("Parola Doğrula")
    
#DECORATOR (KULLANICI GİRİŞİ LAZIM OLDUGU YERDE KULLANIYORUZ)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın","danger")
            return redirect(url_for('login'))
    return decorated_function

#KULLANICI GİRİŞ FORMU
class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")

app=Flask(__name__)
app.secret_key="gorkemblog"
app.config["MYSQL_HOST"] ="localhost"
app.config["MYSQL_USER"] ="root"
app.config["MYSQL_PASSWORD"] =""
app.config["MYSQL_DB"] ="gorkemblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql=MySQL(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
     return render_template("about.html")

#MAKALE SAYFASI
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles"
    result = cursor.execute(sorgu)
    if result > 0:
        articles = cursor.fetchall()     #veritabanındaki TÜM makaleler LİSTE içinde SÖZLÜK olarak döner
        return render_template("articles.html",articles= articles)

    else:
        return render_template("articles.html")

@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles where author =%s"
    result = cursor.execute(sorgu,(session["username"],)) # BURDAKİ YILDIZ "DEMET OLDUGUNU BELLİ EDİYOR"

    if result >0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles = articles)
    else:
        return render_template("dashboard.html")

    return render_template("dashboard.html")

#KAYIT OLMA İŞLEMİ
@app.route("/register",methods =["GET","POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor() #veritabanına kayıt burada tamamlanıyor.
        sorgu ="Insert into users(name,email,username,password) VALUES(%s,%s,%s,%s)"
        cursor.execute(sorgu,(name,email,username,password))
        mysql.connection.commit() #veritabanında herhangi bir güncelleme yapıyorsak yapılır.
        cursor.close() #mysql bağlantısını kapatıyoruz. arkadaki kaynakların gereksiz kullanılmaması için.
        
        flash("Başarıyla Kayıt oldunuz...","success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html",form=form)

#LOGİN İŞLEMİ
@app.route("/login",methods =["GET","POST"])
def login():
    form =LoginForm(request.form)
    if request.method =="POST":
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()
        sorgu ="Select * From users where username = %s"
        result = cursor.execute(sorgu,(username,))

        if result > 0:
            data = cursor.fetchone()
            real_password =data["password"]
            if sha256_crypt.verify(password_entered,real_password): #şifrelenmiş ile girileni kontrol
                flash("Başarıyla Giriş yaptınız","success")

                session["logged_in"] = True
                session["username"] = username

                return redirect(url_for("index"))
            else:
                flash("Parolanızı Yanlış Girdiniz")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir Kullanıcı bulunamadı","danger")
            return redirect(url_for("login"))

    return render_template("login.html",form=form)
# LOGOUT İŞLEMİ
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

#DETAY SAYFASI
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    sorgu = "Select * from articles where id = %s"
    result = cursor.execute(sorgu,(id,))

    if result >0:
        article = cursor.fetchone()
        return render_template("article.html",article =article )
    else:
        return render_template("article.html")

#MAKALE EKLEME 
@app.route("/addarticle",methods = ["GET","POST"])
@login_required
def addarticle():
    form = ArticleForm(request.form)
    if request.method =="POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()
        sorgu = "Insert into articles(title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()

        flash("Makale Başarıyla Eklendi","success")

        return redirect(url_for("dashboard"))
    return render_template("addarticle.html",form = form)

#MAKALE SİLME
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "Select * from articles where author = %s and id = %s"
    result = cursor.execute(sorgu,(session["username"],id))
     
    if result > 0:
        sorgu2 = "Delete from articles where id = %s" 
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle Bir Makale Yok veya Yetkiniz Yok","danger")
        return redirect(url_for("index"))

#MAKALE GÜNCELLEME
@app.route("/edit/<string:id>",methods =["GET","POST"])
@login_required
def update (id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "Select * from articles where id = %s and author = %s"
        result = cursor.execute(sorgu,(id,session["username"]))

        if result ==0:
            flash("Böyle Bir Makale Yok veya Bu işleme Yetkiniz Yok","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html",form=form) #formu html e gönderip gösteriyor burda
    else:
        #POST REQUEST
        form = ArticleForm(request.form)

        newTitle = form.title.data
        newContent = form.content.data

        sorgu2 = "Update articles Set title = %s, content = %s where id= %s"
        cursor = mysql.connection.cursor()
        cursor.execute(sorgu2,(newTitle,newContent,id))
        mysql.connection.commit()
        flash("Makale Başarıyla Güncellendi","success")

        return redirect(url_for("dashboard"))
 

#MAKALE FORM
class ArticleForm(Form):
    title = StringField("Makale Başlığı", validators=[validators.Length(min=5,max=100)])
    content = TextAreaField("Makale İçeriği",validators=[validators.Length(min=10)])

#ARAMA URL
@app.route("/search",methods = ["GET","POST"])
def search():
    if request.method =="GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        sorgu = "Select * from articles where title like '%" + keyword + "%'"
        result = cursor.execute(sorgu)

        if result ==0:
            flash("Aranan Kelimeye Uygun Makale Bulunamadı","danger")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html",articles=articles)

if __name__ == "__main__":
    app.run(debug=True)


