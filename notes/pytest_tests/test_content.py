import pytest
from django.urls import reverse

from news.forms import CommentForm
from news.models import News, Comment


@pytest.mark.django_db
def test_news_count_on_home_page(client, news):
    """
    Количество новостей на главной странице — не более 10.
    """
    # Создаём 11 новостей (settings.NEWS_COUNT_ON_HOME_PAGE + 1)
    from django.conf import settings
    from datetime import timedelta
    from django.utils import timezone

    today = timezone.now()
    for index in range(settings.NEWS_COUNT_ON_HOME_PAGE + 1):
        News.objects.create(
            title=f'Новость {index}',
            text='Просто текст.',
            date=today - timedelta(days=index)
        )

    url = reverse('news:home')
    response = client.get(url)
    object_list = response.context['object_list']

    # Проверяем, что на странице не более 10 новостей
    assert object_list.count() == settings.NEWS_COUNT_ON_HOME_PAGE


@pytest.mark.django_db
def test_news_order_on_home_page(client):
    """
    Новости отсортированы от самой свежей к самой старой.
    """
    from datetime import timedelta
    from django.utils import timezone

    today = timezone.now()
    # Создаём новости с разными датами
    for index in range(5):
        News.objects.create(
            title=f'Новость {index}',
            text='Просто текст.',
            date=today - timedelta(days=index)
        )

    url = reverse('news:home')
    response = client.get(url)
    object_list = response.context['object_list']

    # Получаем даты новостей в порядке вывода
    all_dates = [news.date for news in object_list]
    # Сортируем по убыванию (свежие сначала)
    sorted_dates = sorted(all_dates, reverse=True)

    assert all_dates == sorted_dates


@pytest.mark.django_db
def test_comments_order_on_detail_page(author_client, news, comment):
    """
    Комментарии отсортированы от старых к новым.
    """
    from datetime import timedelta
    from django.utils import timezone

    # Создаём ещё комментарии с разным временем
    now = timezone.now()
    for index in range(5):
        Comment.objects.create(
            news=news,
            author=comment.author,
            text=f'Текст {index}',
            created=now + timedelta(days=index)
        )

    url = reverse('news:detail', args=(news.id,))
    response = author_client.get(url)

    # Получаем объект новости из контекста
    news_obj = response.context['news']
    all_comments = news_obj.comment_set.all()

    # Проверяем порядок — от старых к новым
    all_timestamps = [c.created for c in all_comments]
    sorted_timestamps = sorted(all_timestamps)

    assert all_timestamps == sorted_timestamps


@pytest.mark.django_db
def test_anonymous_client_has_no_form(client, news):
    """
    Анонимный пользователь не видит форму комментария.
    """
    url = reverse('news:detail', args=(news.id,))
    response = client.get(url)
    assert 'form' not in response.context


@pytest.mark.django_db
def test_authorized_client_has_form(author_client, news):
    """
    Авторизованный пользователь видит форму комментария.
    """
    url = reverse('news:detail', args=(news.id,))
    response = author_client.get(url)
    assert 'form' in response.context
    assert isinstance(response.context['form'], CommentForm)
