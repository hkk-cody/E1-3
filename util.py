import time

def print_section(title):
  print("#----------------------------------------")
  print(f"# {title}")
  print("#----------------------------------------")


def read_int(prompt):
  while True:
    try:
      return int(input(prompt).strip())
    except ValueError:
      print("숫자만 입력해주세요.")


def measure_time(func, *args, **kwargs):
  start_time = time.perf_counter()
  func(*args, **kwargs)
  end_time = time.perf_counter()
  elapsed_time = end_time - start_time
  return elapsed_time * 1000  # 밀리초 단위로 반환