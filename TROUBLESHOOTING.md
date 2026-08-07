# Troubleshooting

## "The bot starts fine but never responds to anything"

This turned out to have a real, specific, verified cause - not a hosting
platform issue. If you're on a version of this repo from before this fix,
here's exactly what was wrong and why every symptom pointed the wrong way.

### The actual bug

`Reze/__init__.py` constructs the pyrofork `Client` (and with it, the
internal `Dispatcher`, which binds itself to whatever asyncio event loop
exists at that exact moment). `Reze/__main__.py` used to install `uvloop`
and set up the loop it intended to run everything on.

The problem: **`python3 -m Reze` always executes `Reze/__init__.py`
completely - including constructing the Client - before `Reze/__main__.py`'s
own code even starts running.** This is fundamental to how `-m` works with
packages, not a code-ordering mistake fixable by moving lines around within
`__main__.py`. So `uvloop.install()` living there, no matter how early in
that file, was always too late: the Dispatcher had already bound to a plain
default event loop by the time `__main__.py` ran.

The result: two different event loop objects existed. Handler registration
(`load_plugins()`, which every `@Client.on_message` decorator in
`Reze/modules/*.py` goes through) schedules its work as background tasks on
whichever loop the Dispatcher bound to. The bot actually *ran* on a
different loop entirely. Those registration tasks were scheduled onto a
loop that was created but never run - so they never executed. Not
"slowly" - never, permanently, for the entire life of the process.

**This is invisible from the logs.** Startup looks completely clean:
`Config.validate()` passes, MongoDB connects, `app.start()` returns
successfully, "Reze is armed and ready" logs. Nothing crashes, because
nothing is actually wrong at the level pyrofork's own error handling
watches - the dispatcher just quietly has one handler in it (a built-in
internal one) instead of 125.

The fix: `uvloop.install()` and explicit event loop creation now happen
inside `Reze/__init__.py`, before the `Client(...)` line - the one place
guaranteed to run first regardless of execution method. `Reze/__main__.py`
imports and reuses that exact loop object rather than creating its own.
`Reze/__main__.py` also now explicitly waits for the handler count to
stabilize after `app.start()`, closing a separate, smaller timing gap:
pyrofork's own `initialize()` schedules registration and returns almost
immediately afterward (with `skip_updates=True`, its own default, there's
barely any internal awaiting to give those tasks a chance to run) - so
even with the loop fixed, something has to explicitly wait for
registration to actually finish rather than assume `app.start()` already
did.

### How this was actually found

A raw dispatcher inspection - `len(app.dispatcher.groups)` - printed
directly from a live deployment showed **1 handler** with 30+ modules
loaded. That number, reproduced consistently across two completely
different hosting platforms (Railway and Replit), was the real signal.
Identical behavior across unrelated platforms is strong evidence the
problem lives in the code, not the host - hosting-specific theories
(network drops, connection throttling) should have been deprioritized
much earlier than they were.

This was confirmed by direct reproduction: constructing the real `Client`,
calling the real `load_plugins()`, and checking `dispatcher.groups`
immediately afterward reliably shows exactly 1 handler - 100% repeatable,
not flaky, not environment-dependent. The fix was verified the same way:
via the actual `python3 -m Reze` invocation (not an approximation of it),
confirming the handler count now reaches the full 125 through the genuine
entrypoint.

### A dead end worth naming honestly

A "raw update probe" was suggested as a diagnostic in an earlier version
of this file, using `Client.add_handler(...)` called directly on the
class rather than on the running instance - that's invalid syntax for a
plugin-style handler and the probe never actually ran. If you see that
pattern anywhere, it doesn't work; a raw handler needs to be a proper
`@Client.on_message(...)`-decorated function like every other handler in
this bot, not a bare `add_handler` call.

## If the bot genuinely doesn't respond after this fix

With the loop and registration issues fixed, remaining causes are more
mundane - work through these in order:

1. **Check for a startup error first.** `Config.validate()` fails loudly
   if a required env var is missing. No "Reze is armed and ready" in the
   logs at all means this is it.
2. **`/setprivacy` in @BotFather.** Must be Disabled, or the bot only
   ever sees commands and replies - filters, blacklist, antiflood, and
   locks silently never fire.
3. **A webhook on this bot token.** `Reze/__main__.py` clears this
   automatically on every startup now, but if you're troubleshooting an
   older deployment, worth ruling out explicitly (Telegram delivers
   updates through only one channel at a time).
4. **Wrong service type on the hosting platform.** Some platforms (Koyeb
   among them) distinguish a Web Service (expects a bound port, passes
   HTTP health checks) from a Worker (background process, no port
   needed). This bot is a Worker.
