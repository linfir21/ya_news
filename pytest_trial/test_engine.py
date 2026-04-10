from engine_class import Engine


def test_engine_is_running(engine):
    """Тест проверяет, работает ли двигатель."""
    print('test_engine_is_running')  # Выведем название теста.
    assert engine.is_running


def test_check_engine_class(engine):
    """Тест проверяет класс объекта."""
    print('test_check_engine_class')  # Выведем название теста.
    assert isinstance(engine, Engine)
