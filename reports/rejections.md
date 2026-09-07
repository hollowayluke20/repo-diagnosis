# Rejection report

Attempted: 15  |  Valid: 13  |  Rejected: 2

## Rejections by reason

- **tornado-3** — known test PASSED - bug does not reproduce here
- **luigi-3** — could not run the test: ImportError while importing test module 'C:\Users\hollo\dev\repo-diagnosis\instances\luigi-3\test\parameter_test.py'.

## Valid instances

- **black-2** — python 3.8.3, 74 files / 99184 lines, pile `practice`
- **black-3** — python 3.8.3, 74 files / 99169 lines, pile `practice`
- **tornado-1** — python 3.9 (requested 3.7.0, used 3.9), 112 files / 43398 lines, pile `practice`
- **tornado-2** — python 3.9 (requested 3.7.0, used 3.9), 112 files / 43280 lines, pile `practice`
- **youtube-dl-1** — python 3.9 (requested 3.7.0, used 3.9), 839 files / 134120 lines, pile `practice`, leak risks: ['ChangeLog', 'abcnews.py', 'cbsnews.py', 'ctsnews.py', 'ctvnews.py', 'foxnews.py', 'lifenews.py', 'localnews8.py', 'newstube.py', 'sendtonews.py', 'skynewsarabia.py']
- **youtube-dl-2** — python 3.9 (requested 3.7.0, used 3.9), 830 files / 130070 lines, pile `practice`, leak risks: ['ChangeLog', 'abcnews.py', 'cbsnews.py', 'ctsnews.py', 'ctvnews.py', 'foxnews.py', 'lifenews.py', 'localnews8.py', 'newstube.py', 'sendtonews.py', 'skynewsarabia.py']
- **youtube-dl-3** — python 3.9 (requested 3.7.0, used 3.9), 815 files / 126254 lines, pile `practice`, leak risks: ['ChangeLog', 'abcnews.py', 'cbsnews.py', 'ctsnews.py', 'ctvnews.py', 'foxnews.py', 'lifenews.py', 'localnews8.py', 'newstube.py', 'sendtonews.py', 'skynewsarabia.py']
- **tqdm-2** — python 3.9 (requested 3.6.9, used 3.9), 35 files / 6505 lines, pile `practice`
- **tqdm-3** — python 3.9 (requested 3.6.9, used 3.9), 29 files / 6049 lines, pile `practice`
- **luigi-1** — python 3.8.3, 251 files / 60740 lines, pile `practice`
- **cookiecutter-3** — python 3.9 (requested 3.6.9, used 3.9), 82 files / 7644 lines, pile `practice`, leak risks: ['HISTORY.rst', 'history.rst']
- **httpie-2** — python 3.9 (requested 3.7.3, used 3.9), 46 files / 5708 lines, pile `locked`, leak risks: ['CHANGELOG.rst']
- **sanic-2** — python 3.8.3, 114 files / 20603 lines, pile `practice`, leak risks: ['CHANGELOG.rst', 'changelog.py', 'changelog.rst']
