# Rejection report

Attempted: 20  |  Valid: 12  |  Rejected: 8

## Rejections by reason

- **fastapi-13** — could not run the test: ImportError while importing test module 'C:\Users\hollo\dev\repo-diagnosis\instances\fastapi-13\tests\test_additional_responses_router.py'.
- **spacy-5** — could not run the test: ImportError while loading conftest 'C:\Users\hollo\dev\repo-diagnosis\instances\spacy-5\spacy\tests\conftest.py'.
- **thefuck-13** — could not run the test: ImportError while loading conftest 'C:\Users\hollo\dev\repo-diagnosis\instances\thefuck-13\tests\conftest.py'.
- **tqdm-6** — could not run the test: except ImportError:
- **fastapi-14** — could not run the test: ImportError while importing test module 'C:\Users\hollo\dev\repo-diagnosis\instances\fastapi-14\tests\test_additional_properties.py'.
- **spacy-6** — could not run the test: ImportError while loading conftest 'C:\Users\hollo\dev\repo-diagnosis\instances\spacy-6\spacy\tests\conftest.py'.
- **thefuck-14** — could not run the test: ImportError while loading conftest 'C:\Users\hollo\dev\repo-diagnosis\instances\thefuck-14\tests\conftest.py'.
- **fastapi-15** — could not run the test: ImportError while importing test module 'C:\Users\hollo\dev\repo-diagnosis\instances\fastapi-15\tests\test_ws_router.py'.

## Valid instances

- **PySnooper-3** — python 3.8 (requested 3.8.1, used 3.8), 9 files / 712 lines, pile `locked`
- **black-12** — python 3.8.3, 54 files / 95895 lines, pile `practice`
- **luigi-12** — python 3.8.3, 206 files / 43116 lines, pile `practice`, leak risks: ['changelog']
- **tornado-12** — python 3.9 (requested 3.7.0, used 3.9), 112 files / 39704 lines, pile `practice`
- **youtube-dl-12** — python 3.9 (requested 3.7.4, used 3.9), 868 files / 141654 lines, pile `practice`, leak risks: ['ChangeLog', 'abcnews.py', 'cbsnews.py', 'ctsnews.py', 'ctvnews.py', 'foxnews.py', 'lifenews.py', 'localnews8.py', 'newstube.py', 'sendtonews.py', 'skynewsarabia.py']
- **black-13** — python 3.8.3, 53 files / 95853 lines, pile `locked`
- **luigi-13** — python 3.8.3, 201 files / 42166 lines, pile `locked`, leak risks: ['changelog']
- **tornado-13** — python 3.9 (requested 3.7.0, used 3.9), 113 files / 40341 lines, pile `practice`
- **tqdm-7** — python 3.9 (requested 3.6.9, used 3.9), 24 files / 5326 lines, pile `locked`
- **youtube-dl-13** — python 3.9 (requested 3.7.4, used 3.9), 868 files / 141506 lines, pile `practice`, leak risks: ['ChangeLog', 'abcnews.py', 'cbsnews.py', 'ctsnews.py', 'ctvnews.py', 'foxnews.py', 'lifenews.py', 'localnews8.py', 'newstube.py', 'sendtonews.py', 'skynewsarabia.py']
- **black-14** — python 3.8.3, 51 files / 95624 lines, pile `practice`
- **luigi-14** — python 3.8.3, 201 files / 42149 lines, pile `practice`, leak risks: ['changelog']
