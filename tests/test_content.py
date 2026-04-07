from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from news.forms import CommentForm
from news.models import Comment, News

User = get_user_model()


class TestHomePage(TestCase):
    """
    Тесты главной страницы: количество новостей и их сортировка.
    """

    # URL главной страницы — константа класса
    HOME_URL = reverse('news:home')

    @classmethod
    def setUpTestData(cls):
        """
        Создаём 11 новостей с разными датами
        (больше, чем выводится на главной).
        Используем bulk_create для экономии запросов к БД.
        """
        today = timezone.now()
        all_news = [
            News(
                title=f'Новость {index}',
                text='Просто текст.',
                # Каждая новость старше предыдущей на 1 день
                date=today - timedelta(days=index)
            )
            for index in range(settings.NEWS_COUNT_ON_HOME_PAGE + 1)
        ]
        News.objects.bulk_create(all_news)

    def test_news_count(self):
        """
        На главной странице не более settings.NEWS_COUNT_ON_HOME_PAGE новостей.
        """
        response = self.client.get(self.HOME_URL)
        # Получаем список новостей из контекста шаблона
        object_list = response.context['object_list']
        # Проверяем, что выведено ровно 10 новостей (не 11)
        news_count = object_list.count()
        self.assertEqual(news_count, settings.NEWS_COUNT_ON_HOME_PAGE)

    def test_news_order(self):
        """
        Новости отсортированы от свежих к старым (по убыванию даты).
        """
        response = self.client.get(self.HOME_URL)
        object_list = response.context['object_list']
        # Собираем даты новостей в порядке их вывода на странице
        all_dates = [news.date for news in object_list]
        # Сортируем даты по убыванию (свежие сначала)
        sorted_dates = sorted(all_dates, reverse=True)
        # Проверяем, что порядок на странице совпадает с ожидаемым
        self.assertEqual(all_dates, sorted_dates)


class TestDetailPage(TestCase):
    """
    Тесты страницы отдельной новости: сортировка комментариев и форма.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Создаём новость, автора и 10 комментариев с разным временем создания.
        """
        cls.news = News.objects.create(
            title='Тестовая новость',
            text='Просто текст.'
        )
        # URL страницы новости
        cls.detail_url = reverse('news:detail', args=(cls.news.id,))
        # Пользователь — автор комментариев
        cls.author = User.objects.create(username='Комментатор')
        # Текущее время с учётом часового пояса
        now = timezone.now()
        # Создаём 10 комментариев с увеличивающимся временем создания
        for index in range(10):
            comment = Comment.objects.create(
                news=cls.news,
                author=cls.author,
                text=f'Текст {index}',
            )
            # Принудительно меняем время создания (для теста сортировки)
            comment.created = now + timedelta(days=index)
            comment.save()

    def test_comments_order(self):
        """
        Комментарии отсортированы от старых к новым (по возрастанию даты).
        """
        response = self.client.get(self.detail_url)
        # Проверяем, что в контексте есть объект новости
        self.assertIn('news', response.context)
        # Получаем объект новости из контекста
        news = response.context['news']
        # Получаем все комментарии к новости через related manager
        all_comments = news.comment_set.all()
        # Собираем временные метки комментариев
        all_timestamps = [comment.created for comment in all_comments]
        # Сортируем по возрастанию (старые сначала)
        sorted_timestamps = sorted(all_timestamps)
        # Проверяем порядок сортировки
        self.assertEqual(all_timestamps, sorted_timestamps)

    def test_anonymous_client_has_no_form(self):
        """
        Анонимный пользователь не видит форму комментария.
        """
        response = self.client.get(self.detail_url)
        # Форма отсутствует в словаре контекста
        self.assertNotIn('form', response.context)

    def test_authorized_client_has_form(self):
        """
        Авторизованный пользователь видит форму комментария.
        """
        # Авторизуем клиента
        self.client.force_login(self.author)
        response = self.client.get(self.detail_url)
        # Форма присутствует в контексте
        self.assertIn('form', response.context)
        # И это именно CommentForm
        self.assertIsInstance(response.context['form'], CommentForm)
