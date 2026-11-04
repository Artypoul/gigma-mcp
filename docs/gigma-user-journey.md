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
Подключу вас к Gigma. Нужен только номер телефона.
Токен и пароль не нужны.
```

### Choose

```text
Нашёл существующий проект. Войти в него или зарегистрировать новый проект?
```

Registration additionally asks for a project name.

The choice step has mutually exclusive consent paths. If the host renders the
MCP Apps choice UI/card after `erp_dialog_check`, the agent does not repeat
this text question and does not call `erp_dialog_start` itself. The user's UI
click is the only consent path, and the card starts the selected action. If UI
metadata/card is absent or the host does not render it, use this text fallback
once and call `erp_dialog_start` only after the user's explicit textual
consent. Never present both paths for the same check.

### Callback

```text
Позвоните на показанный номер с телефона, который вы указали.
Повторно звонить не нужно, пока ждём подтверждение текущей попытки.
```

### Connected

```text
Вы подключены к проекту «...».
Сейчас покажу приложения и доступные действия.
```

The agent then reads the safe owner summary and offers the workflow menu.

### Write confirmation

```text
Собираюсь изменить приложение «...»: ...
Изменится: ...
Подтвердить изменение?
```

No write starts before explicit approval.

### Unknown outcome

```text
Сервер не подтвердил, выполнена ли операция.
Я не буду повторять её автоматически. Можно выполнить предусмотренную проверку
или завершить попытку.
```

### Logout

```text
Сессия Gigma завершена. Чтобы продолжить, подключитесь снова.
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
