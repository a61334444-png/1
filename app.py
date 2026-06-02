import os
import sqlite3
from functools import wraps
from pathlib import Path
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'database.db'

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'practice-secret-key-change-in-production')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(reset: bool = False):
    if reset and DB_PATH.exists():
        DB_PATH.unlink()
    conn = get_db()
    cur = conn.cursor()
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin','employer','student')),
        full_name TEXT NOT NULL,
        email TEXT NOT NULL DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS employers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        city TEXT NOT NULL,
        contact_email TEXT NOT NULL,
        website TEXT NOT NULL DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS vacancies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        employer_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        salary TEXT NOT NULL,
        city TEXT NOT NULL,
        employment_type TEXT NOT NULL,
        description TEXT NOT NULL,
        requirements TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY(employer_id) REFERENCES employers(id)
    );
    CREATE TABLE IF NOT EXISTS responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vacancy_id INTEGER NOT NULL,
        user_id INTEGER,
        student_name TEXT NOT NULL,
        email TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(vacancy_id) REFERENCES vacancies(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        text TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        topic TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    ''')

    if cur.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0:
        users = [
            ('admin', generate_password_hash('admin123'), 'admin', 'Администратор системы', 'admin@educareer.ru'),
            ('employer', generate_password_hash('emp123'), 'employer', 'Представитель работодателя', 'employer@educareer.ru'),
            ('student', generate_password_hash('stud123'), 'student', 'Студент-соискатель', 'student@educareer.ru'),
        ]
        cur.executemany('INSERT INTO users(username,password_hash,role,full_name,email) VALUES (?,?,?,?,?)', users)

    if cur.execute('SELECT COUNT(*) FROM employers').fetchone()[0] == 0:
        employers = [
            ('Центр цифрового образования', 'Разрабатывает онлайн-курсы, цифровые учебные материалы и сервисы поддержки студентов.', 'Москва', 'hr@edu-center.ru', 'https://edu-center.example'),
            ('ИТ-лаборатория университета', 'Учебно-научная лаборатория, где студенты участвуют в реальных веб-проектах.', 'Санкт-Петербург', 'jobs@itlab.ru', 'https://itlab.example'),
            ('Академия бизнес-аналитики', 'Образовательный центр подготовки аналитиков, менеджеров цифровых проектов и BI-специалистов.', 'Казань', 'career@analytics.ru', 'https://analytics.example'),
            ('Школа проектного управления', 'Проводит практико-ориентированные программы по управлению ИТ-проектами.', 'Новосибирск', 'pm@project-school.ru', 'https://project-school.example'),
            ('Центр карьерного развития', 'Помогает студентам и выпускникам находить стажировки, вакансии и наставников.', 'Екатеринбург', 'career@students.ru', 'https://students-career.example'),
        ]
        cur.executemany('INSERT INTO employers(name,description,city,contact_email,website) VALUES (?,?,?,?,?)', employers)

    if cur.execute('SELECT COUNT(*) FROM vacancies').fetchone()[0] == 0:
        vacancies = [
            ('Стажер бизнес-аналитик', 3, 'Аналитика', 'от 35 000 руб.', 'Казань', 'Стажировка', 'Сбор требований, описание бизнес-процессов, подготовка пользовательских сценариев.', 'BPMN, внимательность, грамотная письменная речь.'),
            ('Младший Python-разработчик', 2, 'Разработка', 'от 55 000 руб.', 'Санкт-Петербург', 'Полная занятость', 'Разработка внутренних сервисов кафедры и поддержка учебных проектов.', 'Python, Flask/Django, базовые знания SQL и Git.'),
            ('Контент-менеджер образовательного портала', 1, 'Контент', 'от 40 000 руб.', 'Москва', 'Частичная занятость', 'Размещение статей, вакансий, новостей и учебных материалов на портале.', 'Грамотность, HTML на базовом уровне, аккуратность.'),
            ('Специалист технической поддержки', 1, 'Поддержка', 'от 45 000 руб.', 'Москва', 'Сменный график', 'Консультирование пользователей образовательной платформы и регистрация обращений.', 'Коммуникабельность, знание офисных программ, ответственность.'),
            ('Стажер UX/UI-дизайнер', 2, 'Дизайн', 'от 30 000 руб.', 'Удаленно', 'Стажировка', 'Подготовка макетов интерфейсов для образовательных ИТ-сервисов.', 'Figma, понимание юзабилити, портфолио учебных работ.'),
            ('Ассистент менеджера образовательных проектов', 4, 'Управление проектами', 'от 38 000 руб.', 'Новосибирск', 'Частичная занятость', 'Ведение календаря проекта, подготовка отчетов, коммуникация с участниками.', 'Организованность, Excel/Google Sheets, понимание проектного подхода.'),
            ('Аналитик данных начального уровня', 3, 'Аналитика', 'от 60 000 руб.', 'Казань', 'Полная занятость', 'Подготовка отчетов по образовательным программам и визуализация данных.', 'SQL, Excel, основы Power BI или аналогичных BI-инструментов.'),
            ('Модератор карьерной платформы', 5, 'Контент', 'от 32 000 руб.', 'Екатеринбург', 'Удаленно', 'Проверка вакансий, обработка жалоб и актуализация справочников.', 'Внимательность, грамотность, умение работать с регламентами.'),
            ('Frontend-разработчик стажер', 2, 'Разработка', 'от 45 000 руб.', 'Санкт-Петербург', 'Стажировка', 'Верстка страниц, доработка компонентов интерфейса и адаптивности.', 'HTML, CSS, JavaScript, понимание адаптивной верстки.'),
            ('Координатор карьерных мероприятий', 5, 'HR и карьера', 'от 42 000 руб.', 'Екатеринбург', 'Полная занятость', 'Организация вебинаров, дней карьеры и встреч студентов с работодателями.', 'Коммуникабельность, планирование, навыки деловой переписки.'),
            ('Тестировщик образовательной платформы', 1, 'Тестирование', 'от 48 000 руб.', 'Москва', 'Полная занятость', 'Функциональное тестирование сайта, оформление дефектов, проверка исправлений.', 'Тест-кейсы, баг-репорты, внимательность.'),
            ('Специалист по SEO-продвижению', 5, 'Маркетинг', 'от 50 000 руб.', 'Удаленно', 'Проектная работа', 'Подбор ключевых запросов, подготовка рекомендаций по продвижению сайта вакансий.', 'Основы SEO, аналитика посещаемости, работа с текстами.'),
            ('Редактор новостей', 1, 'Контент', 'от 37 000 руб.', 'Москва', 'Частичная занятость', 'Подготовка новостей о стажировках, мероприятиях и карьерных возможностях.', 'Грамотность, умение писать краткие информационные материалы.'),
            ('Администратор базы вакансий', 5, 'Администрирование', 'от 46 000 руб.', 'Екатеринбург', 'Полная занятость', 'Контроль актуальности вакансий, проверка карточек работодателей, работа с пользователями.', 'Ответственность, знание Excel, понимание структуры данных.'),
            ('Методист цифровых курсов', 1, 'Методика', 'от 52 000 руб.', 'Москва', 'Полная занятость', 'Подготовка методических материалов для карьерных онлайн-курсов.', 'Педагогический опыт, структурирование учебных материалов.'),
        ]
        cur.executemany('''INSERT INTO vacancies(title,employer_id,category,salary,city,employment_type,description,requirements)
                           VALUES (?,?,?,?,?,?,?,?)''', vacancies)

    if cur.execute('SELECT COUNT(*) FROM news').fetchone()[0] == 0:
        news_items = [
            ('Открыт набор на стажировки', 'Вакансии', 'На портале опубликованы новые стажировки для студентов направлений бизнес-информатики и цифровой экономики.'),
            ('Обновлена карта работодателей', 'Работодатели', 'В справочник добавлены организации, предлагающие вакансии для начинающих ИТ-специалистов.'),
            ('План карьерного мероприятия', 'Мероприятия', 'Запланирована онлайн-встреча студентов с представителями образовательных компаний.'),
            ('Как подготовить резюме', 'Советы', 'Раздел содержит рекомендации по структуре резюме, описанию учебных проектов и подготовке сопроводительного письма.'),
            ('Пять навыков начинающего аналитика', 'Советы', 'Работодатели чаще всего отмечают важность SQL, описания процессов, визуализации данных, коммуникации и внимательности.'),
            ('Запуск личного кабинета работодателя', 'Обновления', 'Работодатели могут добавлять вакансии и просматривать отклики студентов через защищенный раздел сайта.'),
            ('Версия сайта для слабовидящих', 'Доступность', 'В интерфейс добавлен режим повышенной контрастности и увеличенного шрифта.'),
            ('Подборка удаленных вакансий', 'Вакансии', 'На сайте появились предложения удаленной занятости для студентов, совмещающих работу с учебой.'),
            ('Памятка по прохождению стажировки', 'Советы', 'Перед выходом на стажировку рекомендуется уточнить график, задачи, наставника и порядок отчетности.'),
            ('Обновлен поиск по сайту', 'Обновления', 'Поиск учитывает название вакансии, описание, работодателя, город и категорию.'),
        ]
        cur.executemany('INSERT INTO news(title,category,text) VALUES (?,?,?)', news_items)

    conn.commit()
    conn.close()


def current_user():
    if 'user_id' not in session:
        return None
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
    conn.close()
    return user


@app.context_processor
def inject_user():
    return {'user': current_user()}


def role_required(*roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                flash('Для доступа необходимо войти в систему.', 'error')
                return redirect(url_for('login'))
            if user['role'] not in roles:
                flash('Недостаточно прав доступа.', 'error')
                return redirect(url_for('dashboard'))
            return func(*args, **kwargs)
        return wrapper
    return decorator


@app.route('/')
def index():
    conn = get_db()
    stats = {
        'vacancies': conn.execute('SELECT COUNT(*) FROM vacancies WHERE is_active=1').fetchone()[0],
        'employers': conn.execute('SELECT COUNT(*) FROM employers').fetchone()[0],
        'news': conn.execute('SELECT COUNT(*) FROM news').fetchone()[0],
    }
    vacancies = conn.execute('''SELECT v.*, e.name employer FROM vacancies v JOIN employers e ON e.id=v.employer_id
                                WHERE v.is_active=1 ORDER BY v.id DESC LIMIT 6''').fetchall()
    news = conn.execute('SELECT * FROM news ORDER BY id DESC LIMIT 5').fetchall()
    conn.close()
    return render_template('index.html', vacancies=vacancies, news=news, stats=stats)


@app.route('/vacancies')
def vacancies():
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    city = request.args.get('city', '').strip()
    sql = '''SELECT v.*, e.name employer FROM vacancies v JOIN employers e ON e.id=v.employer_id WHERE v.is_active=1'''
    params = []
    if q:
        sql += ' AND (v.title LIKE ? OR v.description LIKE ? OR v.requirements LIKE ? OR e.name LIKE ?)'
        params.extend([f'%{q}%', f'%{q}%', f'%{q}%', f'%{q}%'])
    if category:
        sql += ' AND v.category=?'
        params.append(category)
    if city:
        sql += ' AND v.city=?'
        params.append(city)
    sql += ' ORDER BY v.id DESC'
    conn = get_db()
    items = conn.execute(sql, params).fetchall()
    categories = conn.execute('SELECT DISTINCT category FROM vacancies ORDER BY category').fetchall()
    cities = conn.execute('SELECT DISTINCT city FROM vacancies ORDER BY city').fetchall()
    conn.close()
    return render_template('vacancies.html', vacancies=items, categories=categories, cities=cities, q=q, selected_category=category, selected_city=city)


@app.route('/vacancy/<int:vacancy_id>', methods=['GET', 'POST'])
def vacancy_detail(vacancy_id):
    conn = get_db()
    vacancy = conn.execute('''SELECT v.*, e.name employer, e.description employer_description, e.contact_email, e.website
                              FROM vacancies v JOIN employers e ON e.id=v.employer_id WHERE v.id=?''', (vacancy_id,)).fetchone()
    if not vacancy:
        conn.close()
        abort(404)
    if request.method == 'POST':
        user = current_user()
        student_name = request.form.get('student_name') or (user['full_name'] if user else '')
        email = request.form.get('email') or (user['email'] if user else '')
        conn.execute('INSERT INTO responses(vacancy_id,user_id,student_name,email,message) VALUES (?,?,?,?,?)',
                     (vacancy_id, user['id'] if user else None, student_name, email, request.form['message']))
        conn.commit()
        conn.close()
        flash('Отклик успешно отправлен.', 'success')
        return redirect(url_for('vacancy_detail', vacancy_id=vacancy_id))
    conn.close()
    return render_template('vacancy_detail.html', vacancy=vacancy)


@app.route('/employers')
def employers():
    conn = get_db()
    items = conn.execute('SELECT * FROM employers ORDER BY name').fetchall()
    conn.close()
    return render_template('employers.html', employers=items)


@app.route('/news')
def news():
    category = request.args.get('category', '').strip()
    conn = get_db()
    if category:
        items = conn.execute('SELECT * FROM news WHERE category=? ORDER BY id DESC', (category,)).fetchall()
    else:
        items = conn.execute('SELECT * FROM news ORDER BY id DESC').fetchall()
    categories = conn.execute('SELECT DISTINCT category FROM news ORDER BY category').fetchall()
    conn.close()
    return render_template('news.html', news=items, categories=categories, selected_category=category)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contacts', methods=['GET', 'POST'])
def contacts():
    if request.method == 'POST':
        conn = get_db()
        conn.execute('INSERT INTO messages(name,email,topic,message) VALUES (?,?,?,?)',
                     (request.form['name'], request.form['email'], request.form['topic'], request.form['message']))
        conn.commit()
        conn.close()
        flash('Сообщение отправлено администратору сайта.', 'success')
        return redirect(url_for('contacts'))
    return render_template('contacts.html')


@app.route('/sitemap')
def sitemap():
    conn = get_db()
    vacancies_list = conn.execute('SELECT id, title FROM vacancies WHERE is_active=1 ORDER BY title').fetchall()
    conn.close()
    return render_template('sitemap.html', vacancies=vacancies_list)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        full_name = request.form['full_name'].strip()
        email = request.form['email'].strip()
        role = request.form.get('role', 'student')
        if role not in ['student', 'employer']:
            role = 'student'
        if len(password) < 6:
            flash('Пароль должен содержать не менее 6 символов.', 'error')
            return render_template('register.html')
        try:
            conn = get_db()
            conn.execute('INSERT INTO users(username,password_hash,role,full_name,email) VALUES (?,?,?,?,?)',
                         (username, generate_password_hash(password), role, full_name, email))
            conn.commit()
            conn.close()
            flash('Регистрация выполнена. Теперь можно войти в систему.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Пользователь с таким логином уже существует.', 'error')
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username=?', (request.form['username'],)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], request.form['password']):
            session['user_id'] = user['id']
            flash('Вход выполнен успешно.', 'success')
            return redirect(url_for('dashboard'))
        flash('Неверный логин или пароль.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы.', 'success')
    return redirect(url_for('index'))


@app.route('/dashboard')
@role_required('admin', 'employer', 'student')
def dashboard():
    user = current_user()
    conn = get_db()
    responses = []
    messages = []
    users = []
    if user['role'] in ['admin', 'employer']:
        responses = conn.execute('''SELECT r.*, v.title vacancy_title, e.name employer
                                    FROM responses r
                                    JOIN vacancies v ON v.id=r.vacancy_id
                                    JOIN employers e ON e.id=v.employer_id
                                    ORDER BY r.id DESC LIMIT 50''').fetchall()
    if user['role'] == 'admin':
        messages = conn.execute('SELECT * FROM messages ORDER BY id DESC LIMIT 20').fetchall()
        users = conn.execute('SELECT id, username, role, full_name, email FROM users ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('dashboard.html', responses=responses, messages=messages, users=users)


@app.route('/admin/vacancy/add', methods=['GET', 'POST'])
@role_required('admin', 'employer')
def add_vacancy():
    conn = get_db()
    employers = conn.execute('SELECT * FROM employers ORDER BY name').fetchall()
    if request.method == 'POST':
        conn.execute('''INSERT INTO vacancies(title,employer_id,category,salary,city,employment_type,description,requirements)
                        VALUES (?,?,?,?,?,?,?,?)''',
                     (request.form['title'], request.form['employer_id'], request.form['category'], request.form['salary'],
                      request.form['city'], request.form['employment_type'], request.form['description'], request.form['requirements']))
        conn.commit()
        conn.close()
        flash('Вакансия добавлена.', 'success')
        return redirect(url_for('vacancies'))
    conn.close()
    return render_template('add_vacancy.html', employers=employers)


@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


init_db()

if __name__ == '__main__':
    app.run(debug=True)
