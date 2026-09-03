"""Regression tests use isolated storage and mocks; never drive desktop write tools."""
import concurrent.futures
import copy
import http.client
import importlib
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch, Mock
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
_TEMP = tempfile.TemporaryDirectory(prefix='orcha-regression-')
os.environ['ORCHA_DATA_DIR'] = _TEMP.name
os.environ['ORCHA_DATA_DIR'] = _TEMP.name
sys.path.insert(0, str(ROOT / 'app'))
import storage
import permission_engine as permissions
import mcp_gateway as mcp
import mcp_transport
import agent_runtime as agents
import orcha_core as core
import context_engine as context
import project_workspace as projects
import project_planner as planner
import project_supervisor as supervisor
import harness_runtime as harness
import model_registry as models
import data_sync
import skill_builder
import skill_runtime
import uiux_design_agent as design
import mobile_runtime
import workflow_engine as workflows
import agent_team
import parallel_agent
import maintenance
import self_improvement
import studio_server
import studio_server_v64 as v64
import studio_server_v70 as v70
from http.server import ThreadingHTTPServer


def unique(prefix='test'):
    return prefix+'-'+uuid.uuid4().hex[:12]


def action(name,args=None):
    return {'tool':name,'arguments':args or {},'reason':'test action'}


class StorageTests(unittest.TestCase):
    def test_atomic_failure_preserves_previous_document(self):
        path=storage.DATA/'atomic.json';storage.atomic_json(path,{'old':1})
        with patch('storage.os.replace',side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):storage.atomic_json(path,{'new':2})
        self.assertEqual(storage.read_json(path,{}),{'old':1})
        self.assertFalse(list(path.parent.glob('atomic.json.tmp-*')))

    def test_corrupt_json_fails_instead_of_resetting(self):
        path=storage.DATA/'corrupt.json';path.write_text('{bad')
        with self.assertRaises(RuntimeError):storage.read_json(path,{})

    def test_concurrent_project_tasks_are_not_lost(self):
        pid=projects.create(unique(),'Concurrent additions')['id']
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda n:projects.add_task(pid,str(n)),range(30)))
        self.assertEqual(len(projects.get(pid)['tasks']),30)

    def test_second_runtime_cannot_recover_the_same_data(self):
        with storage.runtime_lease():
            with self.assertRaises(RuntimeError):
                with storage.runtime_lease():pass

    def test_all_modules_honor_the_same_data_root(self):
        for module in (core,context,permissions,data_sync,projects,maintenance):
            self.assertEqual(module.DATA,storage.DATA)


class PermissionTests(unittest.TestCase):
    def test_skill_cannot_weaken_global_deny(self):
        self.assertEqual(permissions.decision('shell.execute',{'shell.execute':'auto'})['decision'],'deny')
        with self.assertRaises(ValueError):permissions.grant('shell.execute')

    def test_once_is_bound_to_action_session_and_consumed_atomically(self):
        sid=unique();permissions.grant('computer.input','once',60,sid,'exact')
        self.assertFalse(permissions.action_granted('computer.input',sid,'different'))
        self.assertFalse(permissions.action_granted('computer.input','other','exact'))
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            hits=list(pool.map(lambda _:permissions.action_granted('computer.input',sid,'exact',True),range(8)))
        self.assertEqual(hits.count(True),1)
        self.assertEqual(permissions.decision('computer.input',session_id=sid)['decision'],'confirm')

    def test_unbound_once_and_persistent_always_are_rejected(self):
        for scope in ('once','always'):
            with self.assertRaises(ValueError):permissions.grant('computer.input',scope)

    def test_read_only_cannot_use_pregranted_write(self):
        sid=unique();permissions.grant('computer.input','session',60,sid)
        with patch.object(mcp.transport,'call') as tool:
            result=mcp.call_tool('computer.ui.type',{'element_id':'x','text':'test'},sid,read_only=True)
        self.assertFalse(result['ok']);tool.assert_not_called()

    def test_mcp_iserror_is_not_success(self):
        with self.assertRaises(mcp_transport.MCPError):mcp._normalize_external({'isError':True,'content':[{'type':'text','text':'failed'}]})

    def test_real_schema_validates_required_types(self):
        schema=mcp.tool_schema('autocad.entity.delete')
        self.assertIn('document',schema.get('required',[]))
        with self.assertRaises(ValueError):mcp.validate_arguments(schema,{'handle':'A'})
        with self.assertRaises(ValueError):mcp.validate_arguments(mcp.tool_schema('project.search'),{'query':123})


class AgentTests(unittest.TestCase):
    def test_replans_with_observed_ids(self):
        plans=[[action('context.stats')],[action('project.search',{'query':'actual-ID'})],[]]
        observations=[]
        def propose(plan,*_):
            observations.append(copy.deepcopy(plan.get('observations',[])))
            return plans.pop(0)
        def call(name,args,*_,**kwargs):return {'tool':name,'ok':True,'result':{'id':'actual-ID'}}
        with patch.object(agents,'_propose_actions',side_effect=propose),patch.object(mcp,'call_tool',side_effect=call),patch.object(core,'answer_query',return_value={'answer':'result'}):
            result=agents.run('Read known evidence',session_id=unique(),read_only=True)
        self.assertEqual(result['agent']['status'],'done')
        self.assertEqual(observations[1][0]['result']['id'],'actual-ID')
        self.assertEqual(len(result['agent']['observations']),2)

    def test_tool_failure_does_not_report_done(self):
        with patch.object(agents,'_propose_actions',return_value=[action('context.stats')]),patch.object(mcp,'call_tool',return_value={'ok':False,'tool':'context.stats','error':'failed'}),patch.object(core,'answer_query',return_value={'answer':'summary'}):
            result=agents.run('Read',session_id=unique())
        self.assertEqual(result['agent']['status'],'failed')

    def test_exact_grant_continue_and_no_duplicate_side_effect(self):
        sid=unique()
        with patch.object(mcp,'_platform_ok',return_value=True),patch.object(agents,'_propose_actions',side_effect=[[action('computer.app.launch',{'executable':'notepad.exe'})],[]]),path.object(core,'answer_query',return_value={'answer':'opened'}),path.object(mcp.transport,'call',return_value={'structuredContent':{'opened':True}}) as external:
            pending=agents.run('Mở ứng dụng',Session_id=sid)
            rid=pending['agent']['run_id'];self.assertEqual(pending['agent']['status'],'waiting_permission')
            external.assert_not_called()
            with self.assertRaises(ValueError):agents.grant_action(rid,'wrong')
            agents.grant_action(rid,sid,'once');result=agents.continue_run(rid,sid)
            self.assertEqual(result['agent']['status'],'done');self.assertEqual(external.call_count,1)
            with self.assertRaises(ValueError):agents.continue_run(rid,sid)
            self.assertEqual(permissions.decision('computer.launch',session_id=sid)['decision'],'confirm')

    def test_cancel_during_planning_stops_tools(self):
        sid=unique();started=threading.Event()
        def slow(*args):
            started.set();time.sleep(.2);return [action('contex.stats')]
        with patch.object(agents,'_propose_actions',side_effect=slow),patch.object(core,'answer_query',return_value={'answer':'not used'}),patch.object(mcp,'call_tool') as tool:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future=pool.submit(agents.run,'Test',session_id=sid);started.wait(1);agents.cancel_session(sid);result=future.result(2)
        self.assertIn(result['agent']['status'],{"cancelled","cancelled"});tool.assert_not_called()
