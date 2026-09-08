# Rejection report

Attempted: 20  |  Valid: 11  |  Rejected: 9

## Rejections by reason

- **fastapi-16** — could not run the test: ImportError while importing test module 'C:\Users\hollo\dev\repo-diagnosis\instances\fastapi-16\tests\test_jsonable_encoder.py'.
- **spacy-7** — could not run the test: ImportError while loading conftest 'C:\Users\hollo\dev\repo-diagnosis\instances\spacy-7\spacy\tests\conftest.py'.
- **thefuck-15** — could not run the test: ImportError while loading conftest 'C:\Users\hollo\dev\repo-diagnosis\instances\thefuck-15\tests\conftest.py'.
- **fastapi-4** — could not run the test: ImportError while importing test module 'C:\Users\hollo\dev\repo-diagnosis\instances\fastapi-4\tests\test_param_in_path_and_dependency.py'.
- **spacy-8** — could not run the test: ImportError while loading conftest 'C:\Users\hollo\dev\repo-diagnosis\instances\spacy-8\spacy\tests\conftest.py'.
- **thefuck-16** — could not run the test: ImportError while loading conftest 'C:\Users\hollo\dev\repo-diagnosis\instances\thefuck-16\tests\conftest.py'.
- **fastapi-5** — could not run the test: ImportError while importing test module 'C:\Users\hollo\dev\repo-diagnosis\instances\fastapi-5\tests\test_filter_pydantic_sub_model.py'.
- **luigi-17** — could not run the test: E   ModuleNotFoundError: No module named 'sqlalchemy'
- **spacy-9** — could not run the test: ImportError while loading conftest 'C:\Users\hollo\dev\repo-diagnosis\instances\spacy-9\spacy\tests\conftest.py'.

## Valid instances

- **black-15** — python 3.8.3, 50 files / 95606 lines, pile `locked`
- **luigi-15** — python 3.8.3, 198 files / 41032 lines, pile `locked`, leak risks: ['changelog']
- **tornado-14** — python 3.9 (requested 3.7.0, used 3.9), 108 files / 38825 lines, pile `practice`
- **tqdm-8** — python 3.9 (requested 3.6.9, used 3.9), 18 files / 3517 lines, pile `locked`
- **youtube-dl-14** — python 3.9 (requested 3.7.4, used 3.9), 850 files / 145867 lines, pile `locked`, leak risks: ['ChangeLog', 'abcnews.py', 'cbsnews.py', 'ctsnews.py', 'ctvnews.py', 'foxnews.py', 'lifenews.py', 'localnews8.py', 'newstube.py', 'sendtonews.py', 'skynewsarabia.py', 'trunews.py']
- **black-16** — python 3.8.3, 50 files / 95404 lines, pile `locked`
- **luigi-16** — python 3.8.3, 192 files / 38721 lines, pile `practice`, leak risks: ['changelog']
- **tornado-15** — python 3.9 (requested 3.7.0, used 3.9), 108 files / 38197 lines, pile `locked`
- **tqdm-9** — python 3.9 (requested 3.6.9, used 3.9), 7 files / 999 lines, pile `locked`
- **youtube-dl-15** — python 3.9 (requested 3.7.4, used 3.9), 831 files / 130948 lines, pile `practice`, leak risks: ['ChangeLog', 'abcnews.py', 'cbsnews.py', 'ctsnews.py', 'ctvnews.py', 'foxnews.py', 'lifenews.py', 'localnews8.py', 'newstube.py', 'sendtonews.py', 'skynewsarabia.py']
- **black-17** — python 3.8.3, 43 files / 10500 lines, pile `practice`
