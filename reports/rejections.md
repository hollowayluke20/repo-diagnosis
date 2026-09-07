# Rejection report

Attempted: 34  |  Valid: 16  |  Rejected: 18

## Rejections by reason

- **cookiecutter-2** — validation test still present after cleanup
- **cookiecutter-3** — validation test still present after cleanup
- **httpie-2** — validation test still present after cleanup
- **sanic-2** — validation test still present after cleanup
- **tqdm-1** — test errored rather than failed: no tests ran in 0.00s
ERROR: file or directory not found: python3 -m pytest tqdm/tests/tests_contrib.py::test_enumerate
- **tqdm-2** — test errored rather than failed: no tests ran in 0.00s
ERROR: file or directory not found: python3 -m pytest tqdm/tests/tests_tqdm.py::test_format_meter
- **tqdm-3** — test errored rather than failed: no tests ran in 0.00s
ERROR: file or directory not found: python3 -m pytest tqdm/tests/tests_tqdm.py::test_bool
- **black-1** — test errored rather than failed: ERROR: usage: __main__.py [options] [file_or_dir] [file_or_dir] [...]
__main__.py: error: argument -q/--quiet: ignored explicit argument ' tests.test_black.BlackTestCase.test_works_in_mono_process_only_environment'
- **black-2** — test errored rather than failed: ERROR: usage: __main__.py [options] [file_or_dir] [file_or_dir] [...]
__main__.py: error: argument -q/--quiet: ignored explicit argument ' tests.test_black.BlackTestCase.test_fmtonoff4'
- **black-3** — test errored rather than failed: ERROR: usage: __main__.py [options] [file_or_dir] [file_or_dir] [...]
__main__.py: error: argument -q/--quiet: ignored explicit argument ' tests.test_black.BlackTestCase.test_invalid_config_return_code'
- **luigi-1** — test errored rather than failed: cs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
ERROR test/server_test.py
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!
2 warnings, 1 error in 0.51s
ERROR: found no collectors for C:\Users\hollo\dev\repo-diagnosis\instances\luigi-1\test\server_test.py::MetricsHandlerTest::test_get
- **luigi-3** — test errored rather than failed: ble/how-to/capture-warnings.html
=========================== short test summary info ===========================
ERROR test/parameter_test.py
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!
2 warnings, 1 error in 0.29s
ERROR: found no collectors for C:\Users\hollo\dev\repo-diagnosis\instances\luigi-3\test\parameter_test.py::TestSerializeTupleParameter::testSerialize
- **tornado-1** — test errored rather than failed: ERROR: usage: __main__.py [options] [file_or_dir] [file_or_dir] [...]
__main__.py: error: argument -q/--quiet: ignored explicit argument ' tornado.test.websocket_test.WebSocketTest.test_nodelay'
- **tornado-2** — test errored rather than failed: ERROR: usage: __main__.py [options] [file_or_dir] [file_or_dir] [...]
__main__.py: error: argument -q/--quiet: ignored explicit argument ' tornado.test.httpclient_test.HTTPClientCommonTestCase.test_redirect_put_without_body'
- **tornado-3** — test errored rather than failed: ERROR: usage: __main__.py [options] [file_or_dir] [file_or_dir] [...]
__main__.py: error: argument -q/--quiet: ignored explicit argument ' tornado.test.httpclient_test.SyncHTTPClientSubprocessTest'
- **youtube-dl-1** — test errored rather than failed: ERROR: usage: __main__.py [options] [file_or_dir] [file_or_dir] [...]
__main__.py: error: argument -q/--quiet: ignored explicit argument ' test.test_utils.TestUtil.test_match_str'
- **youtube-dl-2** — test errored rather than failed: ERROR: usage: __main__.py [options] [file_or_dir] [file_or_dir] [...]
__main__.py: error: argument -q/--quiet: ignored explicit argument ' test.test_InfoExtractor.TestInfoExtractor.test_parse_mpd_formats'
- **youtube-dl-3** — test errored rather than failed: ERROR: usage: __main__.py [options] [file_or_dir] [file_or_dir] [...]
__main__.py: error: argument -q/--quiet: ignored explicit argument ' test.test_utils.TestUtil.test_unescape_html'

## Valid instances

- **cookiecutter-4** — python 3.9 (requested 3.6.9, used 3.9), 58 files / 4874 lines, pile `practice`, leak risks: ['HISTORY.rst', 'history.rst']
- **httpie-1** — python 3.9 (requested 3.7.3, used 3.9), 48 files / 6094 lines, pile `practice`, leak risks: ['CHANGELOG.rst']
- **httpie-3** — python 3.9 (requested 3.7.3, used 3.9), 45 files / 5651 lines, pile `practice`, leak risks: ['CHANGELOG.rst']
- **sanic-1** — python 3.8.3, 115 files / 20577 lines, pile `practice`, leak risks: ['CHANGELOG.rst', 'changelog.py', 'changelog.rst']
- **sanic-3** — python 3.8.3, 115 files / 20694 lines, pile `practice`, leak risks: ['CHANGELOG.rst', 'changelog.py', 'changelog.rst']
- **thefuck-1** — python 3.9 (requested 3.7.0, used 3.9), 385 files / 15304 lines, pile `practice`
- **thefuck-2** — python 3.9 (requested 3.7.0, used 3.9), 365 files / 14160 lines, pile `locked`
- **thefuck-3** — python 3.9 (requested 3.7.0, used 3.9), 359 files / 13985 lines, pile `practice`
- **thefuck-4** — python 3.9 (requested 3.7.0, used 3.9), 350 files / 13585 lines, pile `practice`
- **luigi-2** — python 3.8.3, 251 files / 60734 lines, pile `locked`
- **fastapi-1** — python 3.8.3, 502 files / 28855 lines, pile `locked`, leak risks: ['release-notes.md']
- **fastapi-2** — python 3.8.3, 485 files / 28400 lines, pile `practice`, leak risks: ['release-notes.md']
- **fastapi-3** — python 3.8.3, 483 files / 28246 lines, pile `practice`, leak risks: ['release-notes.md']
- **spacy-1** — python 3.9 (requested 3.7.7, used 3.9), 684 files / 127625 lines, pile `practice`, leak risks: ['changelog.js', 'newsletter.js', 'newsletter.module.sass']
- **spacy-2** — python 3.9 (requested 3.7.7, used 3.9), 674 files / 127182 lines, pile `practice`, leak risks: ['changelog.js', 'newsletter.js', 'newsletter.module.sass']
- **spacy-3** — python 3.9 (requested 3.7.7, used 3.9), 672 files / 128457 lines, pile `locked`, leak risks: ['changelog.js', 'newsletter.js', 'newsletter.module.sass']
