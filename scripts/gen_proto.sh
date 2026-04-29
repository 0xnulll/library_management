#!/usr/bin/env bash
# Regenerate Python and TypeScript stubs from the proto contracts.
# Run from the repo root: ./scripts/gen_proto.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROTO_DIR="${ROOT_DIR}/proto"
PY_OUT="${ROOT_DIR}/backend/app/grpc_gen"
TS_OUT="${ROOT_DIR}/frontend/lib/proto"

mkdir -p "${PY_OUT}" "${TS_OUT}"

PROTOS=( "${PROTO_DIR}/common.proto" "${PROTO_DIR}/auth.proto" "${PROTO_DIR}/book.proto" "${PROTO_DIR}/member.proto" "${PROTO_DIR}/loan.proto" )

echo "[gen_proto] python -> ${PY_OUT}"
python -m grpc_tools.protoc \
  -I "${PROTO_DIR}" \
  --python_out="${PY_OUT}" \
  --grpc_python_out="${PY_OUT}" \
  --pyi_out="${PY_OUT}" \
  "${PROTOS[@]}"

# grpc_tools emits absolute imports rooted at the proto include path which
# breaks when the package is imported as ``app.grpc_gen``. Rewrite them to
# package-relative imports so the generated files work without sys.path tricks.
# python "${ROOT_DIR}/scripts/_fix_py_imports.py" "${PY_OUT}"

# Make sure the package is importable.
touch "${PY_OUT}/__init__.py"

echo "[gen_proto] typescript -> ${TS_OUT}"
cd "${ROOT_DIR}/frontend"
if [ ! -x node_modules/.bin/protoc-gen-ts_proto ]; then
  echo "[gen_proto] installing frontend deps (ts-proto missing)"
  npm install --no-audit --no-fund --silent
fi
PROTOC_GEN_TS_PROTO="$(pwd)/node_modules/.bin/protoc-gen-ts_proto"

# ts-proto with grpc-web client implementation.
python -m grpc_tools.protoc \
  --plugin=protoc-gen-ts_proto="${PROTOC_GEN_TS_PROTO}" \
  -I "${PROTO_DIR}" \
  --ts_proto_out="${TS_OUT}" \
  --ts_proto_opt=esModuleInterop=true,outputClientImpl=grpc-web,useExactTypes=false,unrecognizedEnum=false \
  "${PROTOS[@]}"

echo "[gen_proto] done"
