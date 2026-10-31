# Gigma owner user journey

This is the human-facing flow. Tool names are implementation details; the agent
should speak in goals and safe states.

## State machine

```text
not_installed
  → installed
  → callback_choice
  → waiting_callback
  → callback_verified
  → connected
  → operating
  → logged_out
```

Terminal states are `expired`, `cancelled`, `provider_outcome_unknown` and
`recovery_required`. They require the action described in the troubleshooting
guide.

## What the user sees

### Connect

```text
Подключу владельца Gigma. Нужен только номер телефона.
Токен или пароль присылать не нужно.
```

### Choose

```text
Нашёл существующий проект. Войти или зарегистрировать новый?
```

Registration additionally asks for a project name.

### Callback

```text
Позвоните на показанный номер с того же телефона.
Новый звонок запускать не нужно, пока эта попытка ожидает подтверждение.
```

### Connected

```text
Вы подключены к проекту «...».
Сейчас покажу приложения и доступные операции.
```

The agent then reads the safe owner summary and offers the workflow menu.

### Write confirmation

```text
Я изменю приложение «...»: ...
Это затронет ...
Продолжить?
```

No write starts before explicit approval.

### Unknown outcome

```text
Сервер не подтвердил результат операции.
Я не буду повторять её автоматически. Можно выполнить поддержанную проверку
или остановить попытку.
```

### Logout

```text
Сессия Gigma завершена. Для следующей операции потребуется новое подключение.
```

## Cross-message rule

The agent may continue the flow across multiple chat messages, but the user
never becomes a transport for opaque capabilities. If state is lost, the agent
uses status/recovery only when the server supports it; otherwise it starts a
new check after the old attempt is terminal.

## Completion

A user journey is complete only when the user can:

- install the package;
- connect or register through the callback;
- understand the current workspace;
- choose a read or write goal;
- approve a write;
- receive a safe result or bounded error;
- disconnect and know how to reconnect.
