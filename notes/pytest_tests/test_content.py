import pytest
from django.urls import reverse

from news.forms import CommentForm


@pytest.mark.django_db  # ← добавить маркер
def test_news_in_list(news, client):
    """Новости видны всем."""
    url = reverse('news:home')
    response = client.get(url)
    object_list = response.context['object_list']
    assert news in object_list


def test_detail_page_contains_form(author_client, news):
    """На странице новости есть форма комментария."""
    url = reverse('news:detail', args=(news.id,))
    response = author_client.get(url)
    assert 'form' in response.context
    assert isinstance(response.context['form'], CommentForm)
