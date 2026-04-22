from util import print_section, measure_time

class mode1:
  def __init__(self, row=3, col=3, epsilon=1e-9):
    self.row = row
    self.col = col
    self.epsilon = epsilon
    #NOTE - 필터 입력
    print_section("[1] 필터 입력")
    self.filter_a = self.read_filter_rows(self.row, self.col, f"필터 A ({self.row}줄 입력, 공백 구분)")
    self.filter_b = self.read_filter_rows(self.row, self.col, f"필터 B ({self.row}줄 입력, 공백 구분)")
    #NOTE - 패턴 입력
    print_section("[2] 패턴 입력")
    self.pattern = self.read_filter_rows(self.row, self.col, f"패턴 ({self.row}줄 입력, 공백 구분)")

    #NOTE - MAC 결과
    print_section("[3] MAC 결과")
    self.result()

  def read_int_row(self, col_count):
    while True:
      try:
        row = list(map(int, input().split()))
        if (len(row) != col_count):
          raise ValueError
        for num in row:
          if num not in [0, 1]:
            raise ValueError
        return row
      except ValueError:
        print(f"{col_count}개의 0 또는 1을 입력해주세요.")

  def read_filter_rows(self, row_count, col_count, prompt):
    rows = []
    print(f"{prompt}")
    for _ in range(row_count):
      row = self.read_int_row(col_count)
      rows.append(row)
    print()
    return rows

  def mac(self, filter):
    ret = 0.0
    for i in range(len(filter)):
      for j in range(len(filter[0])):
        ret += filter[i][j] * self.pattern[i][j]
    return ret

  def result(self):
    score_a = self.mac(self.filter_a)
    score_b = self.mac(self.filter_b)
    print(f"A 점수: {score_a}")
    print(f"B 점수: {score_b}")
    avg_time = 0.0
    for _ in range(10):
      avg_time += measure_time(self.mac, self.filter_a)
    avg_time /= 10
    print(f"10회 평균 MAC 계산 시간: {avg_time:.3f} ms")

    if abs(score_a - score_b) < self.epsilon:
      print("판정: A와 B가 비겼습니다. 판정 불가(|A-B| < 1e-9)")
    elif score_a > score_b:
      print("판정: A가 이겼습니다.")
    else:
      print("판정: B가 이겼습니다.")