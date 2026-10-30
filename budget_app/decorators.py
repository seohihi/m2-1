import sys
import functools
from typing import Callable, Any


def handle_cli_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    스택트레이스 출력을 방지하고, 에러 원인 및 해결 힌트를 출력하며
    오류 시 exit code 1로 종료하는 데코레이터입니다.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            print("\n[안내] 작업을 취소했습니다.")
            sys.exit(0)
        except ValueError as e:
            print(f"[오류] {e}")
            print("[힌트] 입력값의 형식이나 범위를 확인해 주세요.")
            sys.exit(1)
        except Exception as e:
            print(f"[오류] 시스템 오류가 발생했습니다: {e}")
            print("[힌트] 명령어가 올바른지 다시 확인해 주세요.")
            sys.exit(1)
    return wrapper