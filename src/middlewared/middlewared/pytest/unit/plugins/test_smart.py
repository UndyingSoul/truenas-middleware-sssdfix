import textwrap

import pytest

from middlewared.plugins.smart import parse_smart_selftest_results, parse_current_smart_selftest


def test__parse_smart_selftest_results__ataprint__1():
    assert parse_smart_selftest_results(textwrap.dedent("""\
        smartctl 6.6 2017-11-05 r4594 [FreeBSD 11.1-STABLE amd64] (local build)
        Copyright (C) 2002-17, Bruce Allen, Christian Franke, www.smartmontools.org

        === START OF READ SMART DATA SECTION ===
        SMART Self-test log structure revision number 1
        Num  Test_Description    Status                  Remaining  LifeTime(hours)  LBA_of_first_error
        # 1  Short offline       Completed without error       00%     16590         -
        # 2  Short offline       Completed without error       00%     16589         -
    """)) == [
        {
            "num": 1,
            "description": "Short offline",
            "status": "SUCCESS",
            "status_verbose": "Completed without error",
            "remaining": 0.0,
            "lifetime": 16590,
            "lba_of_first_error": None,
        },
        {
            "num": 2,
            "description": "Short offline",
            "status": "SUCCESS",
            "status_verbose": "Completed without error",
            "remaining": 0.0,
            "lifetime": 16589,
            "lba_of_first_error": None,
        }
    ]


def test__parse_smart_selftest_results__ataprint__2():
    assert parse_smart_selftest_results(textwrap.dedent("""\
        Num  Test_Description    Status                  Remaining  LifeTime(hours)  LBA_of_first_error
        # 1  Offline             Self-test routine in progress 100%         0         -
    """)) == [
        {
            "num": 1,
            "description": "Offline",
            "status": "RUNNING",
            "status_verbose": "Self-test routine in progress",
            "remaining": 1.0,
            "lifetime": 0,
            "lba_of_first_error": None,
        },
    ]


@pytest.mark.parametrize("line,subresult", [
    # Longest possible error message
    ("# 1  Extended offline    Completed: servo/seek failure 80%      2941         -", {
        "status": "FAILED",
        "status_verbose": "Completed: servo/seek failure",
        "remaining": 0.8,
    }),
    # Test in progress
    ("# 1  Selective offline   Self-test routine in progress 90%       352         -", {
        "status": "RUNNING",
    })
])
def test__parse_smart_selftest_results__ataprint(line, subresult):
    hdr = "Num  Test_Description    Status                  Remaining  LifeTime(hours)  LBA_of_first_error"
    assert {k: v for k, v in parse_smart_selftest_results(f"{hdr}\n{line}")[0].items() if k in subresult} == subresult


def test__parse_smart_selftest_results__nvmeprint__1():
    assert parse_smart_selftest_results(textwrap.dedent("""\
        Self-test Log (NVMe Log 0x06)
        Self-test status: No self-test in progress
        Num  Test_Description  Status                       Power_on_Hours  Failing_LBA  NSID Seg SCT Code
         0   Short             Completed without error               18636            -     -   - 0x0 0x00
    """)) == [
        {
            "num": 0,
            "description": "Short",
            "status": "SUCCESS",
            "status_verbose": "Completed without error",
            "power_on_hours": 18636,
            "failing_lba": None,
            "nsid": None,
            "seg": None,
            "sct": "0x0",
            "code": "0x00",
        },
    ]


def test__parse_smart_selftest_results__scsiprint__1():
    assert parse_smart_selftest_results(textwrap.dedent("""\
        smartctl version 5.37 [i686-pc-linux-gnu] Copyright (C) 2002-6 Bruce Allen
        Home page is http://smartmontools.sourceforge.net/
        SMART Self-test log
        Num  Test              Status                 segment  LifeTime  LBA_first_err [SK ASC ASQ]
             Description                              number   (hours)
        # 1  Background short  Completed, segment failed   -    3943                 - [-   -    -]
    """)) == [
        {
            "num": 1,
            "description": "Background short",
            "status": "FAILED",
            "status_verbose": "Completed, segment failed",
            "segment_number": None,
            "lifetime": 3943,
            "lba_of_first_error": None,
        },
    ]


@pytest.mark.parametrize("stdout,result", [
    # ataprint.cpp
    (
        textwrap.dedent("""\
            === START OF READ SMART DATA SECTION ===
            Self-test execution status:        41% of test remaining
            SMART Self-test log
        """),
        {"progress": 59},
    ),
    # nvmeprint.cpp
    (
        textwrap.dedent("""\
            Self-test Log (NVMe Log 0x06)
            Self-test status: Short self-test in progress (3% completed)
            No Self-tests Logged
        """),
        {"progress": 3},
    ),
    # scsiprint.spp
    (
        textwrap.dedent("""\
            Self-test execution status:      (   0)	The previous self-test routine completed
                                             without error or no self-test has ever 
                                             been run.

        """),
        None,
    ),
    (
        textwrap.dedent("""\
            Self-test execution status:      ( 242)	Self-test routine in progress...
                                                    20% of test remaining.
        """),
        {"progress": 80},
    ),
    (
        textwrap.dedent("""\
            SMART Self-test log
            Num  Test              Status                 segment  LifeTime  LBA_first_err [SK ASC ASQ]
                 Description                              number   (hours)
            # 1  Background short  Self test in progress ...   -     NOW                 - [-   -    -]
        """),
        {"progress": 0},
    )
])
def test__parse_current_smart_selftest(stdout, result):
    assert parse_current_smart_selftest(stdout) == result
