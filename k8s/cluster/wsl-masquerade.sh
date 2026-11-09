#!/bin/bash
# WSL 미러 네트워크에서 k3s 파드가 인터넷(공공 API)에 못 나가는 문제를 고쳐요. root로 실행해요
#
# 왜: 파드에서 나가는 연결은 flannel이 PC 주소로 바꾸면서(MASQUERADE) 출발 포트를 무작위로(--random-fully) 다시 골라요.
#     WSL 미러 모드는 정해진 범위(/proc/sys/net/ipv4/ip_local_port_range) 밖 포트로 오는 답장을 버려서, 연결이 시간 초과돼요.
#     (docker compose에서는 docker-compose.override.yml의 sysctls로 해결한 같은 문제)
# 어떻게: flannel 규칙보다 먼저, '파드 → 클러스터 밖' 연결만 WSL 범위 안의 포트로 바꾸는 규칙을 맨 앞에 넣어요.
#
# 한 번 실행:     sudo bash k8s/cluster/wsl-masquerade.sh
# 매번 자동으로:  sudo bash k8s/cluster/wsl-masquerade.sh install   (k3s가 켜질 때마다 실행되게 등록)
# 되돌리기:       sudo bash k8s/cluster/wsl-masquerade.sh remove
set -euo pipefail

PODS=10.42.0.0/16
read -r LOW HIGH < /proc/sys/net/ipv4/ip_local_port_range

rule() {   # $1 = -C(있나) / -I(넣기) / -D(빼기), $2 = tcp|udp
  if [ "$1" = -I ]; then
    iptables -t nat -I POSTROUTING 1 -s $PODS ! -d $PODS -p "$2" \
      -m comment --comment "wsl-mirrored masq" -j MASQUERADE --to-ports "$LOW-$HIGH"
  else
    iptables -t nat "$1" POSTROUTING -s $PODS ! -d $PODS -p "$2" \
      -m comment --comment "wsl-mirrored masq" -j MASQUERADE --to-ports "$LOW-$HIGH"
  fi
}

apply_rules() {
  for p in tcp udp; do
    rule -C $p 2>/dev/null || rule -I $p   # 이미 있으면 또 넣지 않아요
  done
  echo "넣었어요: 파드 → 밖 연결의 출발 포트를 $LOW-$HIGH 안에서"
}

case "${1:-apply}" in
  apply)
    apply_rules
    ;;
  install)
    # k3s 서비스에 '켜진 뒤 이 스크립트 실행'을 덧붙여요 (k3s 설치 파일은 건드리지 않고 덧붙이기 파일만 만들어요)
    mkdir -p /etc/systemd/system/k3s.service.d
    install -m 755 "$(realpath "$0")" /usr/local/bin/wsl-masquerade.sh
    cat > /etc/systemd/system/k3s.service.d/wsl-masquerade.conf <<'EOF'
[Service]
ExecStartPost=/bin/bash /usr/local/bin/wsl-masquerade.sh apply
EOF
    systemctl daemon-reload
    apply_rules
    echo "등록했어요: k3s가 켜질 때마다 자동으로 넣어요"
    ;;
  remove)
    for p in tcp udp; do
      while rule -C $p 2>/dev/null; do rule -D $p; done
    done
    rm -f /etc/systemd/system/k3s.service.d/wsl-masquerade.conf /usr/local/bin/wsl-masquerade.sh
    systemctl daemon-reload
    echo "뺐어요"
    ;;
esac
