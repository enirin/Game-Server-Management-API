#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
port="${1:-6587}"
log_dir="${script_dir}"
log_file="${2:-${LOG_FILE:-${log_dir}/craftopia-connections.log}}"
log_retention_days="${LOG_RETENTION_DAYS:-3}"
log_max_size_bytes="${LOG_MAX_SIZE_BYTES:-5242880}"
idle_timeout_seconds="${IDLE_TIMEOUT_SECONDS:-8}"

mkdir -p "${log_dir}"

declare -A active_peers=()

cleanup_old_logs() {
  :
}

compact_log_if_needed() {
  local current_size cutoff_timestamp temp_file retained_bytes

  current_size="$(wc -c < "${log_file}" 2>/dev/null || echo 0)"

  if (( current_size < log_max_size_bytes )); then
    return
  fi

  temp_file="$(mktemp)"
  cutoff_timestamp="$(date -d "-${log_retention_days} days" '+%F %T')"

  awk -v cutoff="${cutoff_timestamp}" '
    /^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}/ {
      if (substr($0, 1, 19) >= cutoff) {
        print
      }
      next
    }
    {
      print
    }
  ' "${log_file}" > "${temp_file}"

  retained_bytes="$(wc -c < "${temp_file}" 2>/dev/null || echo 0)"
  if (( retained_bytes > log_max_size_bytes )); then
    tail -c "${log_max_size_bytes}" "${temp_file}" > "${temp_file}.tail"
    mv "${temp_file}.tail" "${temp_file}"
  fi

  cat "${temp_file}" > "${log_file}"
  rm -f "${temp_file}"
}

emit_text() {
  local text="$1"

  printf '%s\n' "${text}"
  compact_log_if_needed
  printf '%s\n' "${text}" >> "${log_file}"
}

current_timestamp() {
  date '+%F %T'
}

extract_ipv4_host() {
  local endpoint="$1"

  endpoint="${endpoint%:}"
  if [[ "${endpoint}" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}\.[0-9]+$ ]]; then
    printf '%s\n' "${endpoint%.*}"
    return 0
  fi

  if [[ "${endpoint}" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]+$ ]]; then
    printf '%s\n' "${endpoint%:*}"
    return 0
  fi

  return 1
}

extract_port() {
  local endpoint="$1"

  endpoint="${endpoint%:}"
  if [[ "${endpoint}" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}\.[0-9]+$ ]]; then
    printf '%s\n' "${endpoint##*.}"
    return 0
  fi

  if [[ "${endpoint}" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]+$ ]]; then
    printf '%s\n' "${endpoint##*:}"
    return 0
  fi

  return 1
}

normalize_endpoint() {
  local endpoint="$1"
  local host port_number

  host="$(extract_ipv4_host "${endpoint}" 2>/dev/null || true)"
  port_number="$(extract_port "${endpoint}" 2>/dev/null || true)"

  [[ -n "${host}" && -n "${port_number}" ]] || return 1
  printf '%s:%s\n' "${host}" "${port_number}"
}

emit_event() {
  local event_type="$1"
  local peer_endpoint="$2"
  local detail="$3"

  if [[ -n "${detail}" ]]; then
    emit_text "$(current_timestamp) ${event_type} ${peer_endpoint} ${detail}"
    return
  fi

  emit_text "$(current_timestamp) ${event_type} ${peer_endpoint}"
}

mark_peer_active() {
  local peer_endpoint="$1"
  local now

  now="$(date +%s)"
  if [[ -z "${active_peers[${peer_endpoint}]:-}" ]]; then
    emit_event "LOGIN" "${peer_endpoint}" ""
  fi

  active_peers["${peer_endpoint}"]="${now}"
}

expire_inactive_peers() {
  local now peer_endpoint last_seen idle_seconds

  now="$(date +%s)"
  for peer_endpoint in "${!active_peers[@]}"; do
    last_seen="${active_peers[${peer_endpoint}]}"
    idle_seconds=$(( now - last_seen ))

    if (( idle_seconds >= idle_timeout_seconds )); then
      emit_event "LOGOUT" "${peer_endpoint}" "idle=${idle_seconds}s"
      unset "active_peers[${peer_endpoint}]"
    fi
  done
}

parse_tcpdump_line() {
  local line="$1"
  local src_token dst_token src_endpoint dst_endpoint src_port dst_port

  [[ "${line}" == *" IP "* ]] || return 1
  src_token="$(printf '%s\n' "${line}" | awk '{for (i = 1; i <= NF; i++) if ($i == "IP") {print $(i + 1); exit}}')"
  dst_token="$(printf '%s\n' "${line}" | awk '{for (i = 1; i <= NF; i++) if ($i == ">") {print $(i + 1); exit}}')"

  [[ -n "${src_token}" && -n "${dst_token}" ]] || return 1

  src_endpoint="$(normalize_endpoint "${src_token}" 2>/dev/null || true)"
  dst_endpoint="$(normalize_endpoint "${dst_token}" 2>/dev/null || true)"
  src_port="$(extract_port "${src_token}" 2>/dev/null || true)"
  dst_port="$(extract_port "${dst_token}" 2>/dev/null || true)"

  if [[ -n "${src_endpoint}" && "${dst_port}" == "${port}" ]]; then
    printf '%s\n' "${src_endpoint}"
    return 0
  fi

  if [[ -n "${dst_endpoint}" && "${src_port}" == "${port}" ]]; then
    printf '%s\n' "${dst_endpoint}"
    return 0
  fi

  return 1
}

watch_tcpdump_stream() {
  local line parsed peer_endpoint

  while true; do
    if IFS= read -r -t 1 line; then
      parsed="$(parse_tcpdump_line "${line}" 2>/dev/null || true)"
      if [[ -n "${parsed}" ]]; then
        peer_endpoint="${parsed}"
        mark_peer_active "${peer_endpoint}"
      fi
    fi

    expire_inactive_peers
  done
}

print_error() {
  printf '%s\n' "$1"
}

print_header() {
  emit_text "Craftopia connection watcher
port: ${port}
log: ${log_file}
retention_days: ${log_retention_days}
max_log_size_bytes: ${log_max_size_bytes}
idle_timeout_seconds: ${idle_timeout_seconds}

"
}

watch_with_tcpdump() {
  print_header
  emit_text "mode: tcpdump
LOGIN は初回通信、LOGOUT は ${idle_timeout_seconds} 秒無通信で判定します。
Ctrl+C で終了

"
  watch_tcpdump_stream < <(tcpdump -l -nn -tttt -i any "port ${port}" 2>/dev/null)
}

cleanup_old_logs

if ! command -v tcpdump >/dev/null 2>&1; then
  print_error "Error: tcpdump がインストールされていないため、想定した接続ログを出力できません。"
  print_error "Install: sudo apt update && sudo apt install -y tcpdump"
  exit 1
fi

if [[ "$(id -u)" -eq 0 ]]; then
  watch_with_tcpdump
fi

if command -v sudo >/dev/null 2>&1; then
  print_header
  emit_text "mode: tcpdump via sudo
sudo 権限が必要です。
LOGIN は初回通信、LOGOUT は ${idle_timeout_seconds} 秒無通信で判定します。

"
  watch_tcpdump_stream < <(sudo tcpdump -l -nn -tttt -i any "port ${port}" 2>/dev/null)
  exit 0
fi

print_error "Error: tcpdump は見つかりましたが、実行権限がありません。root で実行するか sudo を利用してください。"
exit 1