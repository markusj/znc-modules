znc-modules
===========

Custom modules/helpers for ZNC

Contains (at the time this README has been updated):

- timer.py: A module to execute commands with a custom delay. Similar to XChat/HexChat /timer

## timer.py

Usage: 

This module can only be loaded as network module. It will forward the passed `<COMMAND>` with a delay of `<DELAY>` seconds to IRC network `<NETWORK>`.

The timer module responds to direct messages

`/msg *timer <DELAY> <COMMAND>`

and raw IRC commands (as sent by send_raw or perform).

`timer <NETWORK> <DELAY> <COMMAND>`


