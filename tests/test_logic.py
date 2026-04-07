from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from news.forms import BAD_WORDS, WARNING
from news.models import Comment, News

User = get_user_model()


class TestCommentCreation(TestCase):
    """
    Тесты создания комментариев: права доступа и стоп-слова.
    """

    COMMENT_TEXT = 'Текст комментария'

    @classmethod
    def setUpTestData(cls):
        """Создаём новость и авторизованного пользователя."""
        cls.news = News.objects.create(title='Заголовок', text='Текст')
        cls.url = reverse('news:detail', args=(cls.news.id,))
        cls.user = User.objects.create(username='Мимо Крокодил')
        # Создаём авторизованный клиент
        cls.auth_client = Client()
        cls.auth_client.force_login(cls.user)
        # Данные для формы комментария
        cls.form_data = {'text': cls.COMMENT_TEXT}

    def test_anonymous_user_cant_create_comment(self):
        """
        Анонимный пользователь не может создать комментарий.
        """
        # Отправляем POST-запрос от анонимного клиента
        self.client.post(self.url, data=self.form_data)
        # Проверяем, что комментариев в базе ноль
        comments_count = Comment.objects.count()
        self.assertEqual(comments_count, 0)

    def test_user_can_create_comment(self):
        """
        Авторизованный пользователь может создать комментарий.
        """
        # Отправляем POST-запрос от авторизованного клиента
        response = self.auth_client.post(self.url, data=self.form_data)
        # Проверяем редирект на страницу с якорем #comments
        self.assertRedirects(response, f'{self.url}#comments')
        # Проверяем, что создан один комментарий
        self.assertEqual(Comment.objects.count(), 1)
        # Получаем комментарий и проверяем его поля
        comment = Comment.objects.get()
        self.assertEqual(comment.text, self.COMMENT_TEXT)
        self.assertEqual(comment.news, self.news)
        self.assertEqual(comment.author, self.user)

    def test_user_cant_use_bad_words(self):
        """
        Комментарий со стоп-словами не проходит модерацию.
        """
        # Формируем данные с первым стоп-словом из списка
        bad_words_data = {
            'text': f'Какой-то текст, {BAD_WORDS[0]}, еще текст'
        }
        response = self.auth_client.post(self.url, data=bad_words_data)
        # Проверяем ошибку в форме
        form = response.context['form']
        self.assertFormError(
            form=form,
            field='text',
            errors=WARNING
        )
        # Убеждаемся, что комментарий не создан
        self.assertEqual(Comment.objects.count(), 0)


class TestCommentEditDelete(TestCase):
    """
    Тесты редактирования и удаления комментариев.
    """

    COMMENT_TEXT = 'Текст комментария'
    NEW_COMMENT_TEXT = 'Обновлённый комментарий'

    @classmethod
    def setUpTestData(cls):
        """Создаём новость, двух пользователей и комментарий."""
        cls.news = News.objects.create(title='Заголовок', text='Текст')
        news_url = reverse('news:detail', args=(cls.news.id,))
        cls.url_to_comments = news_url + '#comments'

        # Автор комментария
        cls.author = User.objects.create(username='Автор комментария')
        cls.author_client = Client()
        cls.author_client.force_login(cls.author)

        # Другой пользователь (читатель)
        cls.reader = User.objects.create(username='Читатель')
        cls.reader_client = Client()
        cls.reader_client.force_login(cls.reader)

        # Создаём комментарий от имени автора
        cls.comment = Comment.objects.create(
            news=cls.news,
            author=cls.author,
            text=cls.COMMENT_TEXT
        )

        # URL для операций с комментарием
        cls.edit_url = reverse('news:edit', args=(cls.comment.id,))
        cls.delete_url = reverse('news:delete', args=(cls.comment.id,))

        # Данные для редактирования
        cls.form_data = {'text': cls.NEW_COMMENT_TEXT}

    def test_author_can_delete_comment(self):
        """
        Автор может удалить свой комментарий.
        """
        # Отправляем DELETE-запрос от имени автора
        response = self.author_client.delete(self.delete_url)
        # Проверяем редирект и статус
        self.assertRedirects(response, self.url_to_comments)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        # Комментарий удалён
        self.assertEqual(Comment.objects.count(), 0)

    def test_user_cant_delete_comment_of_another_user(self):
        """
        Пользователь не может удалить чужой комментарий.
        """
        # Пытаемся удалить от имени читателя
        response = self.reader_client.delete(self.delete_url)
        # Получаем 404
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        # Комментарий на месте
        self.assertEqual(Comment.objects.count(), 1)

    def test_author_can_edit_comment(self):
        """
        Автор может редактировать свой комментарий.
        """
        # Отправляем POST-запрос на редактирование
        response = self.author_client.post(self.edit_url, data=self.form_data)
        # Проверяем редирект
        self.assertRedirects(response, self.url_to_comments)
        # Обновляем объект из базы и проверяем изменения
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.text, self.NEW_COMMENT_TEXT)

    def test_user_cant_edit_comment_of_another_user(self):
        """
        Пользователь не может редактировать чужой комментарий.
        """
        # Пытаемся редактировать от имени читателя
        response = self.reader_client.post(self.edit_url, data=self.form_data)
        # Получаем 404
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        # Обновляем объект из базы — текст не изменился
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.text, self.COMMENT_TEXT)
