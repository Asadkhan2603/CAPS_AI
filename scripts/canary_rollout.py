from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

COMPONENT_CONFIG = {
    "backend": {
        "canary_manifest": ROOT / "k8s-backend-canary.yaml",
        "canary_ingress_manifest": ROOT / "k8s-backend-canary-ingress.yaml",
        "deployment": "backend",
        "canary_deployment": "backend-canary",
        "container": "backend",
        "canary_ingress": "caps-ai-backend-canary-ingress",
        "expects_release_gate": True,
    },
    "frontend": {
        "canary_manifest": ROOT / "k8s-frontend-canary.yaml",
        "canary_ingress_manifest": ROOT / "k8s-frontend-canary-ingress.yaml",
        "deployment": "frontend",
        "canary_deployment": "frontend-canary",
        "container": "frontend",
        "canary_ingress": "caps-ai-frontend-canary-ingress",
        "expects_release_gate": False,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run staged canary rollout control for CAPS AI Kubernetes deployments.",
    )
    parser.add_argument("component", choices=sorted(COMPONENT_CONFIG))
    parser.add_argument(
        "action",
        choices=["prepare", "promote", "rollback", "disable"],
        help="prepare canary, promote stable deployment, rollback canary exposure, or disable canary resources",
    )
    parser.add_argument("--image", help="Container image to deploy for the selected action.")
    parser.add_argument("--namespace", default=os.getenv("CANARY_NAMESPACE", "caps-ai"))
    parser.add_argument("--weight", type=int, default=10, help="Canary traffic weight percentage (0-100).")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--base-url", default=os.getenv("RELEASE_GATE_BASE_URL", "").strip())
    parser.add_argument("--bearer-token", default=os.getenv("RELEASE_GATE_BEARER_TOKEN", "").strip())
    parser.add_argument("--print-only", action="store_true", help="Print commands without executing them.")
    return parser.parse_args()


def run_command(command: list[str], *, print_only: bool) -> None:
    rendered = " ".join(command)
    print(rendered)
    if print_only:
        return
    subprocess.run(command, check=True)


def rollout_status(namespace: str, deployment: str, timeout_seconds: int, *, print_only: bool) -> None:
    run_command(
        [
            "kubectl",
            "-n",
            namespace,
            "rollout",
            "status",
            f"deployment/{deployment}",
            f"--timeout={timeout_seconds}s",
        ],
        print_only=print_only,
    )


def apply_manifest(path: Path, *, print_only: bool) -> None:
    run_command(["kubectl", "apply", "-f", str(path)], print_only=print_only)


def delete_manifest(path: Path, *, print_only: bool) -> None:
    run_command(["kubectl", "delete", "-f", str(path), "--ignore-not-found=true"], print_only=print_only)


def set_image(namespace: str, deployment: str, container: str, image: str, *, print_only: bool) -> None:
    run_command(
        ["kubectl", "-n", namespace, "set", "image", f"deployment/{deployment}", f"{container}={image}"],
        print_only=print_only,
    )


def set_canary_weight(namespace: str, ingress: str, weight: int, *, print_only: bool) -> None:
    bounded = max(0, min(100, int(weight)))
    run_command(
        [
            "kubectl",
            "-n",
            namespace,
            "annotate",
            "ingress",
            ingress,
            f"nginx.ingress.kubernetes.io/canary-weight={bounded}",
            "--overwrite=true",
        ],
        print_only=print_only,
    )


def scale_deployment(namespace: str, deployment: str, replicas: int, *, print_only: bool) -> None:
    run_command(
        [
            "kubectl",
            "-n",
            namespace,
            "scale",
            f"deployment/{deployment}",
            f"--replicas={max(0, int(replicas))}",
        ],
        print_only=print_only,
    )


def run_release_gate(*, base_url: str, bearer_token: str, print_only: bool) -> None:
    if not base_url or not bearer_token:
        raise SystemExit("Release gate requires --base-url and --bearer-token for remote verification.")
    run_command(
        [
            sys.executable,
            str(ROOT / "scripts" / "release_gate.py"),
            "--base-url",
            base_url,
            "--bearer-token",
            bearer_token,
        ],
        print_only=print_only,
    )


def main() -> int:
    args = parse_args()
    config = COMPONENT_CONFIG[args.component]

    if args.action in {"prepare", "promote"} and not args.image:
        raise SystemExit("--image is required for prepare and promote actions.")

    if args.action == "prepare":
        apply_manifest(config["canary_manifest"], print_only=args.print_only)
        apply_manifest(config["canary_ingress_manifest"], print_only=args.print_only)
        set_image(
            args.namespace,
            config["canary_deployment"],
            config["container"],
            args.image,
            print_only=args.print_only,
        )
        rollout_status(
            args.namespace,
            config["canary_deployment"],
            args.timeout_seconds,
            print_only=args.print_only,
        )
        set_canary_weight(
            args.namespace,
            config["canary_ingress"],
            args.weight,
            print_only=args.print_only,
        )
        if config["expects_release_gate"]:
            run_release_gate(
                base_url=args.base_url,
                bearer_token=args.bearer_token,
                print_only=args.print_only,
            )
        return 0

    if args.action == "promote":
        set_image(
            args.namespace,
            config["deployment"],
            config["container"],
            args.image,
            print_only=args.print_only,
        )
        rollout_status(
            args.namespace,
            config["deployment"],
            args.timeout_seconds,
            print_only=args.print_only,
        )
        if config["expects_release_gate"]:
            run_release_gate(
                base_url=args.base_url,
                bearer_token=args.bearer_token,
                print_only=args.print_only,
            )
        set_canary_weight(args.namespace, config["canary_ingress"], 0, print_only=args.print_only)
        scale_deployment(args.namespace, config["canary_deployment"], 0, print_only=args.print_only)
        return 0

    if args.action == "rollback":
        set_canary_weight(args.namespace, config["canary_ingress"], 0, print_only=args.print_only)
        scale_deployment(args.namespace, config["canary_deployment"], 0, print_only=args.print_only)
        if config["expects_release_gate"]:
            run_release_gate(
                base_url=args.base_url,
                bearer_token=args.bearer_token,
                print_only=args.print_only,
            )
        return 0

    if args.action == "disable":
        set_canary_weight(args.namespace, config["canary_ingress"], 0, print_only=args.print_only)
        scale_deployment(args.namespace, config["canary_deployment"], 0, print_only=args.print_only)
        delete_manifest(config["canary_ingress_manifest"], print_only=args.print_only)
        delete_manifest(config["canary_manifest"], print_only=args.print_only)
        return 0

    raise SystemExit(f"Unsupported action: {args.action}")


if __name__ == "__main__":
    raise SystemExit(main())
