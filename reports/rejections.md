# Rejection report

Attempted: 20  |  Valid: 11  |  Rejected: 9

## Rejections by reason

- **PySnooper-2** — could not run the test: ImportError while importing test module 'C:\Users\hollo\dev\repo-diagnosis\instances\PySnooper-2\tests\test_pysnooper.py'.
- **fastapi-11** — could not run the test: no tests ran in 0.00s
- **sanic-4** — could not run the test: ImportError while loading conftest 'C:\Users\hollo\dev\repo-diagnosis\instances\sanic-4\tests\conftest.py'.
- **spacy-10** — could not run the test: ImportError while loading conftest 'C:\Users\hollo\dev\repo-diagnosis\instances\spacy-10\spacy\tests\conftest.py'.
- **thefuck-10** — could not run the test: ImportError while loading conftest 'C:\Users\hollo\dev\repo-diagnosis\instances\thefuck-10\tests\conftest.py'.
- **fastapi-12** — could not run the test: ImportError while importing test module 'C:\Users\hollo\dev\repo-diagnosis\instances\fastapi-12\tests\test_security_http_bearer_optional.py'.
- **spacy-4** — could not run the test: ImportError while loading conftest 'C:\Users\hollo\dev\repo-diagnosis\instances\spacy-4\spacy\tests\conftest.py'.
- **thefuck-11** — could not run the test: ImportError while loading conftest 'C:\Users\hollo\dev\repo-diagnosis\instances\thefuck-11\tests\conftest.py'.
- **thefuck-12** — could not run the test: ImportError while loading conftest 'C:\Users\hollo\dev\repo-diagnosis\instances\thefuck-12\tests\conftest.py'.

## Valid instances

- **httpie-5** — python 3.9 (requested 3.7.3, used 3.9), 8 files / 1016 lines, pile `practice`
- **luigi-10** — python 3.8.3, 206 files / 45435 lines, pile `practice`, leak risks: ['changelog']
- **tornado-10** — python 3.9 (requested 3.7.0, used 3.9), 121 files / 42973 lines, pile `practice`
- **tqdm-4** — python 3.9 (requested 3.6.9, used 3.9), 29 files / 5899 lines, pile `practice`
- **youtube-dl-10** — python 3.9 (requested 3.7.0, used 3.9), 517 files / 59936 lines, pile `practice`, leak risks: ['abc7news.py', 'cbsnews.py', 'ctsnews.py', 'foxnews.py', 'lifenews.py', 'newstube.py']
- **black-11** — python 3.8.3, 57 files / 96458 lines, pile `locked`
- **luigi-11** — python 3.8.3, 206 files / 45390 lines, pile `locked`, leak risks: ['changelog']
- **sanic-5** — python 3.8.3, 88 files / 13323 lines, pile `practice`, leak risks: ['CHANGELOG.md']
- **tornado-11** — python 3.9 (requested 3.7.0, used 3.9), 114 files / 40628 lines, pile `practice`
- **tqdm-5** — python 3.9 (requested 3.6.9, used 3.9), 27 files / 5722 lines, pile `practice`
- **youtube-dl-11** — python 3.9 (requested 3.7.4, used 3.9), 853 files / 144515 lines, pile `locked`, leak risks: ['ChangeLog', 'abcnews.py', 'cbsnews.py', 'ctsnews.py', 'ctvnews.py', 'foxnews.py', 'lifenews.py', 'localnews8.py', 'newstube.py', 'sendtonews.py', 'skynewsarabia.py', 'trunews.py']
