"""
Robust bandwidth tester (improved):
- Selects best server by simple latency check (HTTP HEAD timings)
- Uses parallel streams (ThreadPoolExecutor) per server to saturate link
- Warm-up + measurement windows
- Repeats test and returns median values for stability

Notes:
- This is an approximation to commercial testers. For bit-for-bit parity use Ookla CLI.
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple
import requests
import statistics
from urllib.parse import urlparse

# sensible public test files (may be slow/unreliable depending on location)
DEFAULT_DOWNLOAD_URLS = [
    'http://speedtest.tele2.net/10MB.zip',
    'http://ipv4.download.thinkbroadband.com/10MB.zip',
]
DEFAULT_UPLOAD_URLS = [
    'https://httpbin.org/post',
    'https://postman-echo.com/post',
]

# small helper to measure simple HTTP HEAD latency
def measure_latency(url: str, timeout: float = 3.0) -> float:
    try:
        start = time.time()
        # Use GET with small timeout and stream=False so it returns quickly
        r = requests.head(url, timeout=timeout)
        r.raise_for_status()
        return (time.time() - start) * 1000.0  # ms
    except Exception:
        # fallback to a large latency
        return float('inf')


def select_best_server(urls: List[str], top_n: int = 1) -> List[str]:
    latencies: List[Tuple[str, float]] = []
    for u in urls:
        lat = measure_latency(u)
        latencies.append((u, lat))
    latencies.sort(key=lambda x: x[1])
    best = [u for u, _ in latencies[:top_n]]
    return best


class BandwidthTester:
    def __init__(self, max_workers: int = 8):
        self.lock = threading.Lock()
        self.test_results = {
            'download_mbps': 0.0,
            'upload_mbps': 0.0,
            'test_status': 'idle',
            'current_phase': 'idle',
            'progress': 0,
            'timestamp': None
        }
        self.is_testing = False
        self.max_workers = max_workers

    def _update_test_state(self, **kwargs):
        with self.lock:
            for key, value in kwargs.items():
                self.test_results[key] = value

    def _download_stream(self, url: str, stop_time: float) -> int:
        bytes_downloaded = 0
        try:
            with requests.get(url, stream=True, timeout=10) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=128 * 1024):
                    if not chunk:
                        break
                    bytes_downloaded += len(chunk)
                    if time.time() >= stop_time:
                        break
        except Exception:
            return bytes_downloaded
        return bytes_downloaded

    def _upload_stream(self, url: str, stop_time: float, chunk: bytes) -> int:
        bytes_uploaded = 0
        session = requests.Session()
        try:
            while time.time() < stop_time:
                try:
                    r = session.post(url, data=chunk, timeout=15)
                    if r.status_code in (200, 201, 202, 204):
                        bytes_uploaded += len(chunk)
                    else:
                        break
                except Exception:
                    break
        finally:
            try:
                session.close()
            except Exception:
                pass
        return bytes_uploaded

    def _measure_download(self, url: str, duration: int, workers: int) -> float:
        stop_time = time.time() + duration
        total_bytes = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(self._download_stream, url, stop_time) for _ in range(workers)]
            for f in as_completed(futures):
                try:
                    total_bytes += f.result()
                except Exception:
                    continue
        mbps = (total_bytes * 8) / (duration * 1_000_000)
        return round(mbps, 2)

    def _measure_upload(self, url: str, duration: int, workers: int) -> float:
        stop_time = time.time() + duration
        total_bytes = 0
        chunk = b'x' * (256 * 1024)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(self._upload_stream, url, stop_time, chunk) for _ in range(workers)]
            for f in as_completed(futures):
                try:
                    total_bytes += f.result()
                except Exception:
                    continue
        mbps = (total_bytes * 8) / (duration * 1_000_000)
        return round(mbps, 2)

    def run_capacity_test(self, duration: int = 15, workers: int = 8, repeats: int = 3,
                          download_urls: List[str] = None, upload_urls: List[str] = None) -> dict:
        if self.is_testing:
            return {'status': 'error', 'message': 'Test already running'}

        download_urls = download_urls or DEFAULT_DOWNLOAD_URLS
        upload_urls = upload_urls or DEFAULT_UPLOAD_URLS

        with self.lock:
            self.is_testing = True
            self.test_results['test_status'] = 'testing'
            self.test_results['current_phase'] = 'starting'
            self.test_results['progress'] = 0

        try:
            # select best download/upload server
            best_down = select_best_server(download_urls, top_n=1)[0]
            best_up = select_best_server(upload_urls, top_n=1)[0]

            dl_results = []
            ul_results = []
            total_steps = max(1, repeats * 2 + 2)
            completed_steps = 0

            # small warmup to ramp up TCP
            warmup = max(2, int(min(5, duration // 4)))
            self._update_test_state(current_phase='upload_warmup', progress=round((completed_steps / total_steps) * 100))
            _ = self._measure_upload(best_up, warmup, min(workers, 2))
            completed_steps += 1

            self._update_test_state(current_phase='upload', progress=round((completed_steps / total_steps) * 100))

            # measure upload first, then download
            for i in range(repeats):
                ul = self._measure_upload(best_up, duration, workers)
                ul_results.append(ul)
                completed_steps += 1
                self._update_test_state(upload_mbps=round(statistics.median(ul_results), 2), current_phase='upload', progress=round((completed_steps / total_steps) * 100))
                time.sleep(0.5)

            self._update_test_state(current_phase='download_warmup', progress=round((completed_steps / total_steps) * 100))
            _ = self._measure_download(best_down, warmup, min(workers, 2))
            completed_steps += 1

            self._update_test_state(current_phase='download', progress=round((completed_steps / total_steps) * 100))

            for i in range(repeats):
                dl = self._measure_download(best_down, duration, workers)
                dl_results.append(dl)
                completed_steps += 1
                self._update_test_state(download_mbps=round(statistics.median(dl_results), 2), current_phase='download', progress=round((completed_steps / total_steps) * 100))
                time.sleep(0.5)

            # take median for stability
            final_dl = round(statistics.median(dl_results), 2) if dl_results else 0.0
            final_ul = round(statistics.median(ul_results), 2) if ul_results else 0.0

            with self.lock:
                self.test_results['download_mbps'] = final_dl
                self.test_results['upload_mbps'] = final_ul
                self.test_results['test_status'] = 'complete'
                self.test_results['current_phase'] = 'complete'
                self.test_results['progress'] = 100
                self.test_results['timestamp'] = time.time()

            return self.get_test_results()

        except Exception as e:
            with self.lock:
                self.test_results['test_status'] = 'error'
                self.test_results['current_phase'] = 'error'
            return {'status': 'error', 'message': str(e)}

        finally:
            with self.lock:
                self.is_testing = False

    def run_async_test(self, duration: int = 15, workers: int = 8, repeats: int = 3,
                       download_urls: List[str] = None, upload_urls: List[str] = None) -> dict:
        if self.is_testing:
            return {'status': 'error', 'message': 'Test already running'}
        thread = threading.Thread(target=self.run_capacity_test, args=(duration, workers, repeats, download_urls, upload_urls), daemon=True)
        thread.start()
        return {'status': 'testing', 'message': 'Capacity test started'}

    def get_test_results(self) -> dict:
        with self.lock:
            return self.test_results.copy()


# singleton accessor
_bandwidth_tester = None

def get_bandwidth_tester():
    global _bandwidth_tester
    if _bandwidth_tester is None:
        _bandwidth_tester = BandwidthTester()
    return _bandwidth_tester
