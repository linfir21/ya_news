from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from news.models import Comment, News

# Получаем модель пользователя (AUTH_USER_MODEL из settings)
User = get_user_model()


class TestRoutes(TestCase):
    """
    Тестирование маршрутов приложения news.
    Проверяем доступность страниц для разных типов пользователей.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Фикстура класса: создаёт тестовые данные ОДИН РАЗ перед всеми тестами.
        Экономит время — не создаём объекты перед каждым тестом.
        """
        # Создаём тестовую новость
        cls.news = News.objects.create(title='Заголовок', text='Текст')

        # Создаём двух пользователей: автора и читателя
        cls.author = User.objects.create(username='Лев Толстой')
        cls.reader = User.objects.create(username='Читатель простой')

        # Создаём комментарий от имени автора к тестовой новости
        cls.comment = Comment.objects.create(
            news=cls.news,
            author=cls.author,
            text='Текст комментария'
        )

    def test_pages_availability(self):
        """
        Проверяем, что основные страницы доступны анонимному пользователю.
        Используем subTest() для проверки нескольких URL в одном тесте.
        """
        # Кортеж пар: (имя_маршрута, позиционные_аргументы)
        # None — если маршрут не принимает аргументов
        urls = (
            ('news:home', None),  # Главная страница
            ('news:detail', (self.news.id,)),  # Страница отдельной новости
            ('users:login', None),  # Страница входа
            ('users:signup', None),  # Страница регистрации
        )

        # Проходим по всем URL и проверяем их доступность
        for name, args in urls:
            # subTest позволяет видеть, какой именно URL упал при ошибке
            with self.subTest(name=name):
                # reverse() строит URL по имени маршрута и аргументам
                url = reverse(name, args=args)

                # Делаем GET-запрос от имени анонимного клиента
                response = self.client.get(url)

                # Проверяем, что статус ответа — 200 OK
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_availability_for_comment_edit_and_delete(self):
        """
        Проверяем доступ к редактированию/удалению комментария:
        - Автор комментария должен иметь доступ (HTTP 200)
        - Другой пользователь должен получить 404 (NOT_FOUND)
        """
        # Кортеж пар: (пользователь, ожидаемый_статус)
        users_statuses = (
            (self.author, HTTPStatus.OK),  # Автор — доступ разрешён
            (self.reader, HTTPStatus.NOT_FOUND),  # Читатель — доступ запрещён
        )

        # Внешний цикл: перебираем пользователей и ожидаемые статусы
        for user, status in users_statuses:
            # Программно логиним пользователя в тестовом клиенте
            # После этого все запросы будут от его имени
            self.client.force_login(user)

            # Внутренний цикл: проверяем обе страницы
            # (редактирование и удаление)
            for name in ('news:edit', 'news:delete'):
                with self.subTest(user=user, name=name):
                    # Строим URL с id комментария
                    url = reverse(name, args=(self.comment.id,))

                    # Делаем запрос от имени залогиненного пользователя
                    response = self.client.get(url)

                    # Проверяем, что статус соответствует ожидаемому
                    self.assertEqual(response.status_code, status)

    def test_redirect_for_anonymous_client(self):
        """
        Проверяем, что анонимный пользователь при попытке
        редактировать/удалить чужой комментарий
        редиректится на страницу логина.
        Django добавляет параметр next с адресом исходной страницы.
        """
        # Получаем URL страницы логина (базовый для редиректа)
        login_url = reverse('users:login')

        # Проверяем обе страницы: редактирование и удаление
        for name in ('news:edit', 'news:delete'):
            with self.subTest(name=name):
                # URL страницы, куда пытается зайти аноним
                url = reverse(name, args=(self.comment.id,))

                # Ожидаемый URL редиректа:
                # /auth/login/?next=/news/comment/1/edit/
                # Параметр next позволяет:
                # после логина вернуть пользователя назад
                redirect_url = f'{login_url}?next={url}'

                # Делаем запрос от имени анонима (self.client не залогинен)
                response = self.client.get(url)

                # assertRedirects проверяет:
                # 1. Статус ответа — 302 (редирект)
                # 2. Целевой URL совпадает с ожидаемым
                # 3. Статус целевой страницы — 200 (доступна)
                self.assertRedirects(response, redirect_url)
