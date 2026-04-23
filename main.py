from util import read_int
from mode1 import Mode1
# from mode2 import Mode2

if __name__ == "__main__":
  print("=== Mini NPU Simulator ===\n")
  while True:
    print("[모드 선택]\n")
    print("1. 사용자 입력 (3x3)")
    print("2. data.json 분석")
    choice = read_int("선택: ")
    if choice in [1, 2]:
      break
    print("1 또는 2를 입력해주세요.")

  if choice == 1:
    Mode1()
  else:
    # Mode2("data.json")