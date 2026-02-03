#!/usr/bin/env python3
import sys
sys.path.insert(0, 'apps/backend')

from analysis import CodeQualityAnalyzer
from pathlib import Path
import json

analyzer = CodeQualityAnalyzer(Path('test_code_sample'))
result = analyzer.analyze()
print(json.dumps(result, indent=2))
