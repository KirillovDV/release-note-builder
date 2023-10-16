import os
import subprocess
import requests


class JiraAPI:
    def __init__(self, jira_url, username, password):
        # Инициализация JiraAPI с URL Jira, логином и паролем
        self.jira_url = jira_url
        self.username = username
        self.password = password
        self.auth = (self.username, self.password)  # Создание кортежа для аутентификации
        self.headers = {
            "Content-Type": "application/json"  # Установка типа содержимого
        }

    def get_issue_summary(self, issue_key):
        # Получение краткого описания задачи по ключу задачи
        try:
            issue_url = f"{self.jira_url}/rest/api/2/issue/{issue_key}"  # Сборка URL для запроса задачи
            response = requests.get(issue_url, headers=self.headers,
                                    auth=self.auth)  # Выполнение GET-запроса с аутентификацией

            if response.status_code == 200:  # Проверка успешного ответа
                issue_data = response.json()  # Получение данных задачи
                return issue_data['fields']['summary']  # Возврат краткого описания задачи
            else:
                return None
        except Exception as e:  # Обработка исключений
            return None


# TODO ВЫНЕСТИ ЛОГИН И ПАРОЛЬ ИЗ КОДА!!!!
jira_url = "https://jira.phoenixit.ru"  # Захардкодим URL Jira

# Получение логина и пароля от пользователя
username = input("Введите ваш логин JIRA: ")
password = input("Введите ваш пароль Jira: ")


def retrieve_issue_summary(issue_key):
    jira = JiraAPI(jira_url, username, password)
    issue_summary = jira.get_issue_summary(issue_key)
    return issue_summary


def list_repository_tags(repo_directory):
    # Получение списка тегов в репозитории
    os.chdir(repo_directory)  # Изменение директории на переданный репозиторий
    tag_output = subprocess.check_output(["git", "tag"], text=True)  # Получение списка тегов
    os.chdir(os.path.pardir)  # Возврат на уровень выше
    return tag_output  # Возвращение списка тегов


class GitCommitExtractor:
    def __init__(self):
        self.RELEASE_VERSION_TO = None
        self.RELEASE_VERSION_FROM = None
        self.RELEASE_PRODUCT = input("Введите код продукта: ")  # Продукт (префикс) для поиска в коммитах
        self.unique_commits = {}  # Словарь для хранения уникальных коммитов в каждом репозитории

    def get_versions_from_user(self):
        # Получение версий от пользователя
        self.RELEASE_VERSION_FROM = input("Введите изначальную версию (из списка выше): ")
        self.RELEASE_VERSION_TO = input("Введите конечную версию (из списка выше): ")

        if not self.RELEASE_VERSION_FROM or not self.RELEASE_VERSION_TO:
            print('Введенная версия отсутствует. Выход...')
            exit()

    def process_repositories(self):  # Функция для обработки репозиториев
        current_directory = os.getcwd()  # Получение текущего рабочего каталога

        # Перебор всех элементов в текущем каталоге
        for entry in os.listdir(current_directory):
            if os.path.isdir(entry):  # Проверка, является ли элемент директорией
                repo_directory = os.path.join(current_directory, entry)

                if os.path.exists(os.path.join(repo_directory, '.git')):
                    # Получение списка тегов и вывод названия репозитория
                    tags = list_repository_tags(repo_directory)
                    print(f'Репозиторий: {entry}')
                    print(f'Версии:\n{tags}')

                    # Добавление информации о репозитории и его тегах в словарь
                    if entry not in self.unique_commits:
                        self.unique_commits[entry] = {"tags": tags, "commits": set()}

        # Получение версий от пользователя
        self.get_versions_from_user()

        # Обработка коммитов в каждом репозитории
        for repo, info in self.unique_commits.items():
            self.process_repository(repo, info["tags"])

        # Вывод уникальных коммитов для каждого репозитория
        self.print_unique_commits()

    def process_repository(self, repo_directory, tags):
        os.chdir(repo_directory)
        # Обновление репозитория с помощью git pull & git fetch
        subprocess.run(["git", "fetch"])
        subprocess.run(["git", "pull"])

        # Проверка существования указанных версий в репозитории
        if not self.version_exists(self.RELEASE_VERSION_FROM, tags):
            print(f"Error: Version {self.RELEASE_VERSION_FROM} not found in {repo_directory}.")
        elif not self.version_exists(self.RELEASE_VERSION_TO, tags):
            print(f"Error: Version {self.RELEASE_VERSION_TO} not found in {repo_directory}.")
        else:
            # Извлечение и сохранение коммитов в указанном диапазоне версий
            self.extract_commits(repo_directory)

        os.chdir(os.path.pardir)

    def version_exists(self, version, tags):
        # Проверка существования версии в списке тегов
        return version in tags

    def extract_commits(self, repo_directory):
        # Функция для извлечения и сохранения коммитов с номерами задач

        # Получение вывода команды git log для указанного диапазона версий
        log_output = subprocess.check_output(
            ["git", "log", f"{self.RELEASE_VERSION_FROM}..{self.RELEASE_VERSION_TO}", "--format=%s"], text=True)

        # Разделение вывода на отдельные сообщения коммитов
        commit_messages = log_output.split('\n')

        # Перебор каждого сообщения коммита
        for message in commit_messages:
            if message.lower().startswith(self.RELEASE_PRODUCT.lower()):  # Проверка на соответствие продукту
                task_number = message.split('-')[1].split()[0]  # Извлечение номера задачи
                task_prefix = self.RELEASE_PRODUCT + '-' + task_number  # Сборка префикса задачи
                # Добавление коммита в множество коммитов репозитория
                self.unique_commits[repo_directory]["commits"].add(task_prefix)

    def print_unique_commits(self):
        # Вывод уникальных коммитов для каждого репозитория
        for repo, info in self.unique_commits.items():
            print(f'\n\nRepository: {repo}')
            print("Коммиты:")
            for commit in info["commits"]:
                commit = commit[:-1]
                issue_summary = retrieve_issue_summary(commit)
                print(commit, issue_summary)


if __name__ == "__main__":
    git_commit_extractor = GitCommitExtractor()
    # Запуск программы и обработка репозиториев
    git_commit_extractor.process_repositories()
