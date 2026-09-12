# Трудности инструментов

Проверка planning во внешнем worktree блокируется исправляемой ошибкой.
Windows fixture не может перезаписать скрытый .git в режиме создания файла.
Рассмотрены: r+ с truncate, удаление только fixture-файла с пересозданием,
снятие hidden-атрибута, mock Git topology. Выбран r+: он сохраняет реальный
Git pointer и атрибуты, не добавляет Windows-only API и не ослабляет oracle.

Корневой pytest collection сканирует весь корпус статических проверок времени
даже при выборе одного теста; stack снимок подтвердил задержку до test execution.
Рассмотрены полный scan, ограниченный confcutdir и noconftest. Выбран
`--confcutdir` для отдельной группы, а штатный static checker выполнен отдельно
на изменённом файле. Полная root collection не объявляется пройденной.
Источник: https://docs.pytest.org/en/latest/reference/reference.html .

Длинный временный путь Windows мешал созданию coordination fixture. Рассмотрены
короткий временный корень, process-only core.longpaths и системное изменение.
Короткого temp-корня оказалось достаточно: повтор всех затронутых тестов прошёл,
глобальная Git-конфигурация не менялась. Документация:
https://gitforwindows.org/git-cannot-create-a-file-or-directory-with-a-long-path.html .
Отдельный setup-процесс Git однажды завершился кодом 3221225794; узкий повтор
трёх сценариев прошёл. Этот аварийный запуск не считается успешным тестом.

При подготовке дополнения move-task повторился уже известный сетевой remote-show
в protection preflight. По документации Git рассмотрены: cached `remote show -n`,
локальный symbolic-ref, сетевое чтение HEAD и запись `remote set-head`.
Первые два не восстанавливают отсутствующее знание, последние меняют границу
этой offline-проверки или refs. Для текущего planning выбран прямой запуск
штатных validators документов без выполнения команды и без притворной приёмки.
Полный CLI остаётся непроверенным. Источник: [git-remote](https://git-scm.com/docs/git-remote.html).
