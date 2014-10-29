znc-modules
===========

Custom modules/helpers for ZNC

Contains (at the time this README has been updated):

- timer.py: A module to execute commands with a custom delay. Similar to XChat/HexChat /timer
- awaymonitor.py: A module to set a user away if the last connected client has been disconnected or set away.

## timer.py

Requires ZNC >= 1.5 (the hook OnSendToIRC() which is required to intercept raw IRC commands is supported in ZNC master since 2014-03-04)

This module can only be loaded as network module. It will forward the passed `<COMMAND>` with a delay of `<DELAY>` seconds to IRC network `<NETWORK>`.

The timer module responds to direct messages

`/msg *timer <DELAY> <COMMAND>`

and raw IRC commands (as sent by send_raw or perform).

`timer <NETWORK> <DELAY> <COMMAND>`

## awaymonitor.py

Requires ZNC >= 1.x (the module will most likely work with older releases, but argument passing requires a patch: markusj/znc@79d8ae7432e581e27e40ba19bac4c1161126f8d0)

This module is intented for setups as shown in the [ZNC FAQ](http://wiki.znc.in/FAQ#How_to_store_private_messages_even_when_user_is_attached.2C_so_other_clients_can_see_them.3F). It will set your main user away if each of the connected clients is set away with message "detached" or if any client sets another away message. The module will remember the away state and restore it in case of an IRC reconnect. Together with the module `simple_away` it can be used to forward the auto-away-state to the main user if the last client has been disconnected/detached.

This module accepts one argument (the away message to set if all upstream clients went auto-away) and does not listen to any commands.
