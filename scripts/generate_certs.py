import os
import socket
import subprocess
from pathlib import Path

OPENSSL_PATH = Path(r"C:\Program Files\Git\usr\bin\openssl.exe")
BASE_DIR = Path(__file__).resolve().parent.parent
CERTS_DIR = BASE_DIR / "certs"

def get_ips():
    ips = {"127.0.0.1"}
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if not ip.startswith("169.254."):
                ips.add(ip)
    except Exception:
        pass
    # Also check via socket connection to router/internet
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    return sorted(list(ips))

def generate_certificates():
    CERTS_DIR.mkdir(parents=True, exist_ok=True)
    openssl = str(OPENSSL_PATH) if OPENSSL_PATH.exists() else "openssl"
    
    ca_key = CERTS_DIR / "ca.key"
    ca_crt = CERTS_DIR / "ca.crt"
    server_key = CERTS_DIR / "server.key"
    server_csr = CERTS_DIR / "server.csr"
    server_crt = CERTS_DIR / "server.crt"
    fullchain_crt = CERTS_DIR / "fullchain.crt"
    ca_cnf = CERTS_DIR / "ca.cnf"
    ext_cnf = CERTS_DIR / "san.cnf"

    # 1. Generate Root CA if not exists
    if not ca_key.exists() or not ca_crt.exists():
        print("[CertGen] Generating Root CA...")
        ca_cnf_content = """[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_ca
prompt = no

[req_distinguished_name]
C = US
ST = State
L = City
O = JARVIS Authority
OU = Security
CN = JARVIS Private Root CA

[v3_ca]
basicConstraints = critical, CA:true
keyUsage = critical, digitalSignature, cRLSign, keyCertSign
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
"""
        ca_cnf.write_text(ca_cnf_content, encoding="utf-8")
        subprocess.run([
            openssl, "req", "-x509", "-new", "-nodes",
            "-keyout", str(ca_key),
            "-out", str(ca_crt),
            "-days", "3650",
            "-config", str(ca_cnf)
        ], check=True)
        print(f"[CertGen] Root CA created: {ca_crt}")

    # 2. Collect IPs for SAN
    all_ips = get_ips()
    print(f"[CertGen] Discovered IP addresses for SAN: {all_ips}")
    
    san_entries = ["DNS.1 = localhost", "DNS.2 = jarvis.local"]
    for idx, ip in enumerate(all_ips, start=1):
        san_entries.append(f"IP.{idx} = {ip}")
    
    san_text = "\n".join(san_entries)
    
    ext_content = f"""[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = State
L = City
O = JARVIS
OU = Core Gateway
CN = 192.168.0.154

[v3_req]
basicConstraints = CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
{san_text}
"""
    ext_cnf.write_text(ext_content, encoding="utf-8")

    # 3. Generate server private key & CSR
    print("[CertGen] Generating server key & CSR...")
    subprocess.run([
        openssl, "req", "-new", "-nodes",
        "-out", str(server_csr),
        "-keyout", str(server_key),
        "-config", str(ext_cnf)
    ], check=True)

    # 4. Sign server certificate with CA (800 days for Apple compatibility <= 825)
    print("[CertGen] Signing server certificate with Root CA...")
    subprocess.run([
        openssl, "x509", "-req",
        "-in", str(server_csr),
        "-CA", str(ca_crt),
        "-CAkey", str(ca_key),
        "-CAcreateserial",
        "-out", str(server_crt),
        "-days", "800",
        "-sha256",
        "-extfile", str(ext_cnf),
        "-extensions", "v3_req"
    ], check=True)

    # 5. Build fullchain
    fullchain_crt.write_text(
        server_crt.read_text(encoding="utf-8") + "\n" + ca_crt.read_text(encoding="utf-8"),
        encoding="utf-8"
    )
    print(f"[CertGen] Server certificates ready:")
    print(f"  Root CA:      {ca_crt}")
    print(f"  Server Cert:  {server_crt}")
    print(f"  Full Chain:   {fullchain_crt}")
    print(f"  Server Key:   {server_key}")

if __name__ == "__main__":
    generate_certificates()
