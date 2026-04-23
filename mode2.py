from util import print_section, measure_time
import json
import re

class Mode2:
  ERR_SIZE_KEY_FORMAT = "size 키 형식 오류"
  ERR_PATTERN_KEY_FORMAT = "패턴 키 형식 오류(size_N_idx)"
  ERR_INPUT_NOT_SQUARE = "input이 정사각 2차원 배열이 아님"
  ERR_FILTER_SIZE_MISMATCH = "필터 크기와 size 키 값이 일치하지 않음"
  ERR_INPUT_NON_NUMERIC = "input에 숫자가 아닌 값이 포함됨"
  ERR_MAC_TYPE = "MAC 연산 중 숫자 타입 오류 발생"

  def __init__(self, filename="data.json", epsilon=1e-9):
    """데이터 로드, 분석, 성능 측정, 요약 출력까지 전체 흐름을 초기화한다.

    Args:
      filename: 분석에 사용할 JSON 파일 경로.
      epsilon: Cross/X 점수 비교 시 허용 오차.
    """
    #NOTE - 필터 로드
    self.fail_reasons = {}
    self.results = []
    self.epsilon = epsilon

    print_section("[1] 필터 로드")
    self.data = self.json_load(filename)
    if not self.data:
      print("유효한 JSON 데이터를 로드하지 못했습니다. 프로그램을 종료합니다.")
      return

    self.filters = self.data.get('filters', {})
    self.patterns = self.data.get('patterns', {})

    self.print_filter_load_summary()

    #NOTE - 패턴 분석
    print_section("[2] 패턴 분석 (라벨 정규화 적용)")
    self.analyze_patterns()

    #NOTE - 성능 분석
    print_section("[3] 성능 분석 (평균/10회)")
    self.run_performance_analysis()

    #NOTE - 결과 요약
    print_section("[4] 결과 요약")
    self.print_summary()

  def json_load(self, filename):
    """JSON 파일을 읽고 검증한 뒤 유효한 데이터만 반환한다.

    Args:
      filename: 읽어들일 JSON 파일 경로.

    Returns:
      검증에 통과한 JSON 데이터 딕셔너리, 실패 시 빈 딕셔너리.
    """
    try:
      with open(filename, 'r') as f:
        data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
      print(f"Error loading JSON from {filename}: {e}")
      return {}

    if not self.validate_data(data, filename):
      return {}
    return data

  def validate_data(self, data, filename):
    """JSON 루트 구조와 filters, patterns 데이터를 순서대로 검증한다.

    Args:
      data: JSON에서 파싱한 최상위 객체.
      filename: 오류 메시지 출력에 사용할 파일명.

    Returns:
      모든 검증을 통과하면 True, 아니면 False.
    """
    if not self.validate_json_data(data, filename):
      return False
    filters = data['filters']
    patterns = data['patterns']

    if not self.validate_filters_data(filters, filename):
      return False
    if not self.validate_patterns_data(patterns, filename):
      return False
    return True

  def validate_json_data(self, data, filename):
    """JSON 루트 타입과 필수 키(filters, patterns) 존재 여부를 확인한다.

    Args:
      data: 검증할 JSON 루트 객체.
      filename: 오류 메시지 출력에 사용할 파일명.

    Returns:
      유효하면 True, 아니면 False.
    """
    if not isinstance(data, dict):
      print(f"Error loading JSON from {filename}: JSON root must be an object")
      return False
    if 'filters' not in data:
      print(f"Error loading JSON from {filename}: missing 'filters' key")
      return False
    if 'patterns' not in data:
      print(f"Error loading JSON from {filename}: missing 'patterns' key")
      return False

    filters = data['filters']
    patterns = data['patterns']

    if not isinstance(filters, dict):
      print(f"Error loading JSON from {filename}: 'filters' must be an object")
      return False
    if not isinstance(patterns, dict):
      print(f"Error loading JSON from {filename}: 'patterns' must be an object")
      return False
    return True

  def validate_filters_data(self, filters, filename):
    """필터 키, 라벨, 행렬 크기, 원소 타입을 검증한다.

    Args:
      filters: filters 섹션의 데이터.
      filename: 오류 메시지 출력에 사용할 파일명.

    Returns:
      필터 데이터가 유효하면 True, 아니면 False.
    """
    for filter_key, filter_value in filters.items():
      size = self.parse_size_key(filter_key)
      if size is None:
        print(f"Error loading JSON from {filename}: invalid filter key '{filter_key}' (expected size_N)")
        return False
      if not isinstance(filter_value, dict):
        print(f"Error loading JSON from {filename}: '{filter_key}' must be an object")
        return False

      normalized_labels = set()
      for raw_label, matrix in filter_value.items():
        label = self.normalize_label(raw_label)
        if label is None:
          continue
        normalized_labels.add(label)
        matrix_size = self.matrix_size(matrix)
        if matrix_size is None:
          print(f"Error loading JSON from {filename}: '{filter_key}.{raw_label}' must be an NxN matrix")
          return False
        if matrix_size != size:
          print(f"Error loading JSON from {filename}: '{filter_key}.{raw_label}' size mismatch (matrix={matrix_size}x{matrix_size}, key={size}x{size})")
          return False
        for row in matrix:
          for value in row:
            if not isinstance(value, (int, float)):
              print(f"Error loading JSON from {filename}: '{filter_key}.{raw_label}' contains non-numeric value")
              return False

      if 'Cross' not in normalized_labels or 'X' not in normalized_labels:
        print(f"Error loading JSON from {filename}: '{filter_key}' must include cross/x labels")
        return False
    return True

  def validate_patterns_data(self, patterns, filename):
    """패턴 항목에 input과 expected 구조가 있는지 확인한다.

    Args:
      patterns: patterns 섹션의 데이터.
      filename: 오류 메시지 출력에 사용할 파일명.

    Returns:
      패턴 데이터가 유효하면 True, 아니면 False.
    """
    for pattern_key, pattern_value in patterns.items():
      if not isinstance(pattern_value, dict):
        print(f"Error loading JSON from {filename}: '{pattern_key}' must be an object")
        return False
      if 'input' not in pattern_value:
        print(f"Error loading JSON from {filename}: '{pattern_key}' missing 'input' key")
        return False
      if 'expected' not in pattern_value:
        print(f"Error loading JSON from {filename}: '{pattern_key}' missing 'expected' key")
        return False
      if not isinstance(pattern_value['input'], list):
        print(f"Error loading JSON from {filename}: '{pattern_key}.input' must be a list")
        return False
    return True

  def normalize_label(self, label):
    """라벨 표현을 표준 라벨(Cross, X)로 정규화한다.

    Args:
      label: 원본 라벨 문자열.

    Returns:
      정규화된 라벨 문자열 또는 변환할 수 없으면 None.
    """
    if not isinstance(label, str):
      return None
    lowered = label.strip().lower()
    mapping = {
      '+': 'Cross',
      'cross': 'Cross',
      'x': 'X'
    }
    return mapping.get(lowered)

  def parse_size_key(self, key):
    """size_N 또는 size_N_idx 형태의 키에서 N 값을 추출한다.

    Args:
      key: 크기 정보가 들어 있는 문자열 키.

    Returns:
      파싱된 정수 크기 또는 실패 시 None.
    """
    if not isinstance(key, str):
      return None
    matched = re.fullmatch(r"size_(\d+)(?:_(\d+))?", key)
    if not matched:
      return None
    return int(matched.group(1))

  def matrix_size(self, matrix):
    """정사각 2차원 리스트면 한 변 길이를 반환한다.

    Args:
      matrix: 크기를 검사할 2차원 리스트.

    Returns:
      정사각 행렬이면 한 변 길이, 아니면 None.
    """
    if not isinstance(matrix, list) or len(matrix) == 0:
      return None
    if not isinstance(matrix[0], list):
      return None
    row_len = len(matrix[0])
    if row_len == 0:
      return None
    for row in matrix:
      if not isinstance(row, list) or len(row) != row_len:
        return None
    if len(matrix) != row_len:
      return None
    return len(matrix)

  def get_filter_pair(self, size):
    """지정 크기의 Cross/X 필터를 조회하고 라벨 정규화를 적용한다.

    Args:
      size: 조회할 필터 크기.

    Returns:
      정규화된 필터 딕셔너리와 오류 사유 문자열(None 가능).
    """
    size_key = f"size_{size}"
    if size_key not in self.filters:
      return None, f"필터 '{size_key}'를 찾을 수 없습니다."

    raw_filters = self.filters[size_key]
    if not isinstance(raw_filters, dict):
      return None, f"필터 '{size_key}'는 객체여야 합니다."

    normalized = {}
    for raw_label, filter_matrix in raw_filters.items():
      label = self.normalize_label(raw_label)
      if label is None:
        continue
      normalized[label] = filter_matrix

    if 'Cross' not in normalized or 'X' not in normalized:
      return None, f"필터 '{size_key}'는 cross/x(또는 정규화 가능한 키)를 모두 포함해야 합니다."

    return normalized, None

  def mac(self, pattern, filter_matrix):
    """패턴과 필터의 원소별 곱의 합(MAC 점수)을 계산한다.

    Args:
      pattern: 입력 패턴 행렬.
      filter_matrix: 비교할 필터 행렬.

    Returns:
      계산된 MAC 점수.
    """
    score = 0.0
    for i in range(len(pattern)):
      for j in range(len(pattern[0])):
        score += pattern[i][j] * filter_matrix[i][j]
    return score

  def decide_label(self, cross_score, x_score):
    """두 점수를 비교해 Cross, X, UNDECIDED 중 하나를 결정한다.

    Args:
      cross_score: Cross 필터의 점수.
      x_score: X 필터의 점수.

    Returns:
      최종 판정 라벨 문자열.
    """
    if abs(cross_score - x_score) < self.epsilon:
      return 'UNDECIDED'
    if cross_score > x_score:
      return 'Cross'
    return 'X'

  def print_filter_load_summary(self):
    """크기 순으로 필터 로드 성공/실패 상태를 요약 출력한다."""
    for size_key, size in self.iter_sorted_filter_keys():
      filter_pair, reason = self.get_filter_pair(size) if size is not None else (None, self.ERR_SIZE_KEY_FORMAT)
      if filter_pair is None:
        print(f"- {size_key}: FAIL ({reason})")
      else:
        print(f"✓ {size_key} 필터 로드 완료 (Cross, X)")

  def iter_sorted_filter_keys(self):
    """필터 키를 크기 기준으로 정렬한 리스트를 반환한다.

    Returns:
      (size_key, parsed_size) 튜플로 이루어진 정렬된 리스트.
    """
    return sorted(
      ((size_key, self.parse_size_key(size_key)) for size_key in self.filters),
      key=lambda item: (item[1] is None, item[1] or 0)
    )

  def analyze_patterns(self):
    """각 패턴을 검증하고 채점해 PASS/FAIL 결과를 기록한다."""
    for pattern_key, pattern_value in self.patterns.items():
      context, reason = self.prepare_pattern_context(pattern_key, pattern_value)
      if context is None:
        self.record_fail(pattern_key, reason, pattern_value.get('expected'))
        continue

      try:
        cross_score = self.mac(context['pattern_input'], context['filter_pair']['Cross'])
        x_score = self.mac(context['pattern_input'], context['filter_pair']['X'])
      except TypeError:
        self.record_fail(pattern_key, self.ERR_MAC_TYPE, context['expected_raw'])
        continue

      verdict = self.decide_label(cross_score, x_score)
      expected = context['expected']
      result = 'PASS' if verdict == expected else 'FAIL'

      self.print_pattern_analysis_result(pattern_key, cross_score, x_score, verdict, expected, result)

      if result == 'FAIL':
        self.fail_reasons[pattern_key] = f"판정 불일치(verdict={verdict}, expected={expected})"

      self.append_result(pattern_key, cross_score, x_score, verdict, expected, result)

  def prepare_pattern_context(self, pattern_key, pattern_value):
    """패턴 분석에 필요한 입력 검증과 컨텍스트 구성을 수행한다.

    Args:
      pattern_key: 패턴 식별 키.
      pattern_value: input과 expected를 포함한 패턴 데이터.

    Returns:
      (컨텍스트 딕셔너리, 오류 사유) 형태의 튜플.
    """
    expected_raw = pattern_value.get('expected')
    expected = self.normalize_label(expected_raw)
    pattern_input = pattern_value.get('input')

    size = self.parse_size_key(pattern_key)
    if size is None:
      return None, self.ERR_PATTERN_KEY_FORMAT

    pattern_size = self.matrix_size(pattern_input)
    if pattern_size is None:
      return None, self.ERR_INPUT_NOT_SQUARE

    filter_pair, reason = self.get_filter_pair(size)
    if filter_pair is None:
      return None, reason

    cross_filter_size = self.matrix_size(filter_pair['Cross'])
    x_filter_size = self.matrix_size(filter_pair['X'])
    if cross_filter_size != size or x_filter_size != size:
      return None, self.ERR_FILTER_SIZE_MISMATCH

    if pattern_size != size:
      return None, f"크기 불일치(pattern={pattern_size}x{pattern_size}, filter={size}x{size})"

    if not self.is_numeric_matrix(pattern_input):
      return None, self.ERR_INPUT_NON_NUMERIC

    if expected is None:
      return None, f"expected 라벨 정규화 실패({expected_raw})"

    return {
      'expected_raw': expected_raw,
      'expected': expected,
      'pattern_input': pattern_input,
      'filter_pair': filter_pair,
    }, None

  def print_pattern_analysis_result(self, pattern_key, cross_score, x_score, verdict, expected, result):
    """단일 패턴 분석 결과를 사용자 친화적인 형식으로 출력한다.

    Args:
      pattern_key: 패턴 식별 키.
      cross_score: Cross 점수.
      x_score: X 점수.
      verdict: 최종 판정.
      expected: 기대 라벨.
      result: PASS 또는 FAIL.
    """
    print(f"--- {pattern_key} ---")
    print(f"Cross 점수: {cross_score}")
    print(f"X 점수: {x_score}")
    print(f"판정: {verdict} | expected: {expected} | {result}")

  def append_result(self, pattern_key, cross_score, x_score, verdict, expected, result):
    """분석 결과를 공통 포맷 딕셔너리로 results 리스트에 추가한다.

    Args:
      pattern_key: 패턴 식별 키.
      cross_score: Cross 점수.
      x_score: X 점수.
      verdict: 최종 판정.
      expected: 기대 라벨.
      result: PASS 또는 FAIL.
    """
    self.results.append({
      'key': pattern_key,
      'cross_score': cross_score,
      'x_score': x_score,
      'verdict': verdict,
      'expected': expected,
      'result': result
    })

  def record_fail(self, pattern_key, reason, expected_raw):
    """실패 케이스를 출력하고 실패 사유 및 결과를 저장한다.

    Args:
      pattern_key: 패턴 식별 키.
      reason: 실패 사유.
      expected_raw: 원본 expected 값.
    """
    expected = self.normalize_label(expected_raw)
    expected_text = expected if expected is not None else str(expected_raw)
    print(f"--- {pattern_key} ---")
    print("Cross 점수: N/A")
    print("X 점수: N/A")
    print(f"판정: UNDECIDED | expected: {expected_text} | FAIL ({reason})")
    self.fail_reasons[pattern_key] = reason
    self.append_result(pattern_key, None, None, 'UNDECIDED', expected_text, 'FAIL')

  def is_numeric_matrix(self, matrix):
    """행렬의 모든 원소가 숫자형인지 확인한다.

    Args:
      matrix: 검사할 2차원 리스트.

    Returns:
      모든 원소가 int/float이면 True, 아니면 False.
    """
    for row in matrix:
      for value in row:
        if not isinstance(value, (int, float)):
          return False
    return True

  def run_performance_analysis(self):
    """여러 크기에서 MAC 연산 평균 시간을 측정해 표로 출력한다."""
    print(f"{'크기':<8}{'평균 시간(ms)':>13}{'연산 횟수':>12}")
    print("-" * 41)

    for size in [3, 5, 13, 25]:
      filter_matrix = self.select_performance_filter(size)
      pattern = self.generate_cross_pattern(size)

      total_ms = 0.0
      for _ in range(10):
        total_ms += measure_time(self.mac, pattern, filter_matrix)
      avg_ms = total_ms / 10
      ops = size * size

      size_text = f"{size}x{size}"
      print(f"{size_text:<6}{avg_ms:>13.3f}{ops:>20}")

  def select_performance_filter(self, size):
    """성능 측정용 필터를 선택하고 없으면 기본 Cross 패턴을 반환한다.

    Args:
      size: 성능 측정에 사용할 크기.

    Returns:
      선택된 필터 행렬.
    """
    filter_pair, _ = self.get_filter_pair(size)
    if filter_pair is not None:
      return filter_pair['Cross']
    return self.generate_cross_pattern(size)

  def generate_cross_pattern(self, size):
    """십자 모양(중앙 행/열이 1)인 size x size 패턴 행렬을 생성한다.

    Args:
      size: 생성할 행렬의 한 변 길이.

    Returns:
      생성된 십자 패턴 행렬.
    """
    mid = size // 2
    matrix = []
    for i in range(size):
      row = []
      for j in range(size):
        if i == mid or j == mid:
          row.append(1)
        else:
          row.append(0)
      matrix.append(row)
    return matrix

  def print_summary(self):
    """전체 테스트의 통과/실패 집계를 출력하고 실패 목록을 보여준다."""
    total = len(self.results)
    passed = sum(1 for result in self.results if result['result'] == 'PASS')
    failed = total - passed

    print(f"총 테스트: {total}개")
    print(f"통과: {passed}개")
    print(f"실패: {failed}개")

    if failed > 0:
      print("\n실패 케이스:")
      for case_key, reason in self.fail_reasons.items():
        print(f"- {case_key}: {reason}")
