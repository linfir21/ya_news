from http import HTTPStatus

import pytest
from django.urls import reverse
from pytest_django.asserts import assertFormError, assertRedirects

from news.forms import WARNING
from news.models import Comment


@pytest.fixture
def form_data():
    return {
        'text': 'Текст комментария',
    }


@pytest.mark.django_db
def test_anonymous_user_cant_create_comment(client, form_data, news):
    """Анонимный пользователь не может создать комментарий."""
    url = reverse('news:detail', args=(news.id,))
    response = client.post(url, data=form_data)
    login_url = reverse('users:login')
    expected_url = f'{login_url}?next={url}'
    assertRedirects(response, expected_url)
    assert Comment.objects.count() == 0


def test_user_can_create_comment(author_client, author, form_data, news):
    """Авторизованный пользователь может создать комментарий."""
    url = reverse('news:detail', args=(news.id,))
    response = author_client.post(url, data=form_data)
    # Редирект на ту же страницу с якорем #comments
    assertRedirects(response, f'{url}#comments')
    assert Comment.objects.count() == 1
    new_comment = Comment.objects.get()
    assert new_comment.text == form_data['text']
    assert new_comment.news == news
    assert new_comment.author == author


def test_user_cant_use_bad_words(author_client, form_data, news):
    """Комментарий со стоп-словами не проходит."""
    from news.forms import BAD_WORDS
    form_data['text'] = f'Какой-то текст, {BAD_WORDS[0]}, еще текст'
    url = reverse('news:detail', args=(news.id,))
    response = author_client.post(url, data=form_data)
    assertFormError(
        response.context['form'],
        'text',
        errors=WARNING,
    )
    assert Comment.objects.count() == 0


def test_author_can_edit_comment(author_client, form_data, comment):
    """Автор может редактировать свой комментарий."""
    url = reverse('news:edit', args=(comment.id,))
    response = author_client.post(url, form_data)
    assertRedirects(response, reverse('news:detail',
                                      args=(comment.news.id,)) + '#comments')
    comment.refresh_from_db()
    assert comment.text == form_data['text']


def test_other_user_cant_edit_comment(not_author_client, form_data, comment):
    """Другой пользователь не может редактировать чужой комментарий."""
    url = reverse('news:edit', args=(comment.id,))
    response = not_author_client.post(url, form_data)
    assert response.status_code == HTTPStatus.NOT_FOUND
    comment_from_db = Comment.objects.get(id=comment.id)
    assert comment.text == comment_from_db.text


def test_author_can_delete_comment(author_client, comment):
    """Автор может удалить свой комментарий."""
    url = reverse('news:delete', args=(comment.id,))
    response = author_client.post(url)
    assertRedirects(response, reverse('news:detail',
                                      args=(comment.news.id,)) + '#comments')
    assert Comment.objects.count() == 0


def test_other_user_cant_delete_comment(not_author_client, comment):
    """Другой пользователь не может удалить чужой комментарий."""
    url = reverse('news:delete', args=(comment.id,))
    response = not_author_client.post(url)
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert Comment.objects.count() == 1
