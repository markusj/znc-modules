znc-modules
===========

Custom modules/helpers for ZNC

Contains (at the time this README has been updated):

- timer.py: A module to execute commands with a custom delay. Similar to XChat/HexChat /timer
- awaymonitor.py: A module to set a user away if the last connected client has been disconnected or set away.
- titelbot.py: A voting bot used in freenode/##happyshooting to to vote for a show/podcast title. There might be other use cases, too.

## timer.py

Requires ZNC >= 1.5 (the hook OnSendToIRC() which is required to intercept raw IRC commands is supported in ZNC master since 2014-03-04). If the module is used in an environment where different users have network configurations with identical names, a ZNC build newer than 2015-01-11 is required.

This module can only be loaded as network module. It will forward the passed `<COMMAND>` with a delay of `<DELAY>` seconds to the assigned IRC network.

The timer module responds to direct messages

`/msg *timer <DELAY> <COMMAND>`

and raw IRC commands (as sent by send_raw or perform).

`timer <DELAY> <COMMAND>`

## awaymonitor.py

Requires ZNC >= 1.5 (passing arguments to Python modules has been broken before 2014-10-29)

This module is intented for setups as shown in the [ZNC FAQ](http://wiki.znc.in/FAQ#How_to_store_private_messages_even_when_user_is_attached.2C_so_other_clients_can_see_them.3F). It will set your main user away if each of the connected clients is set away with message "detached" or if any client sets another away message. The module will remember the away state and restore it in case of an IRC reconnect. Together with the module `simple_away` it can be used to forward the auto-away-state to the main user if the last client has been disconnected/detached.

This module accepts one argument (the away message to set if all upstream clients went auto-away) and does not listen to any commands.

## titlebot.py

Requires ZNC >= 1.5 (passing arguments to Python modules has been broken before 2014-10-29)

This module has been developed primarily for the channel freenode/##happyshooting, to offer a live-voting for titles of the german photo podcast [Happy Shooting](http://www.happyshooting.de/podcast/).
The bot is able to run multiple votings in parallel (but limited to one voting per channel).

The module accepts an argument string formatted like:

`<channel> <activator_char> <admin_user> <more_admin_users> : <channel> ...`

Where `<activator_char>` denotes the character signaling there comes a command, for example `!` in case of `!help`. The administrative users have full control of the voting process while regular users can only add proposals, vote, revoke their own vote and list all proposals/options.

Tho bot itself does not join or part any channels on its own, ZNC offers distinct facilities and modules for this task.

The most important commands are `help`, `vote`, `revoke`, `add`, `list` and for admins `enable`, `disable`, `reset` and `del`
