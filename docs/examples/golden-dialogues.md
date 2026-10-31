# Golden dialogues

These examples define the expected user-facing behavior. They do not contain
capabilities, tokens, callback proofs, phone numbers or provider secrets.

## Existing owner

User: \`Подключи меня к Gigma.\`

Agent: asks for the phone, calls the check tool, presents the project result,
and asks the user to choose login or registration.

After the callback is verified, the agent reads the owner summary and offers
applications, subscriptions, payment review, investigation and logout.

## New owner

The agent asks for a project name only after the user explicitly chooses
registration. It never infers consent from \`project_exists\`.

## Pending callback

The agent says that the callback is waiting and does not start another callback.
It polls with bounded progress and waits for the user to call from the same
phone.

## Unknown callback outcome

For \`provider_outcome_unknown\` or \`recovery_required\`, the agent stops,
explains that the result is not confirmed, and asks whether to use the explicit
supported recovery action. It never silently restarts.

## Safe write

User: \`Создай приложение для сайта, но сначала покажи, что изменится.\`

The agent reads current applications, presents the proposed name and state,
asks for approval, calls the create tool once, and reports the safe result.

## Payment evidence

The agent warns that evidence must not contain secrets, tokens, card data,
OTP, provider payloads or unnecessary personal data. It asks for approval before
saving operator evidence and never echoes the evidence.

## ERP request

User: \`Добавь склад и товары.\`

The agent explains that warehouses and nomenclature belong to the ERP API
contour, not this owner MCP package. It does not call an arbitrary REST or SQL
operation.

## Lost state

If the host loses the opaque state, the agent does not ask the user to paste it.
It reports that recovery or a fresh check is required and keeps the old attempt
terminal before starting another one.

## Logout

User: \`Отключи меня от Gigma.\`

The agent revokes the session, discards capability state and says that a new
connection is required for later work.
