-- Demo data for the local container run. Re-runnable. IPs are from the documentation ranges (RFC 5737).
-- The probes are simulated by backend/utils/probe_sim.py; 192.0.2.99 is a probe that is deliberately offline.
CREATE TABLE IF NOT EXISTS b11_huck_ge_probes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  server_private_ip VARCHAR(255), isp_expected VARCHAR(255), city VARCHAR(255),
  public_ip VARCHAR(255), isp VARCHAR(255), hostname VARCHAR(255), country VARCHAR(255)
);
CREATE TABLE IF NOT EXISTS c10_for_paping_probes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  server_ip VARCHAR(255), which_isp VARCHAR(255), which_city VARCHAR(255)
);
CREATE TABLE IF NOT EXISTS a97_whitelist_conditions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  condition_type VARCHAR(20), condition_pattern VARCHAR(500), condition_name VARCHAR(200),
  description VARCHAR(500), is_enabled TINYINT(1) DEFAULT 1, is_built_in TINYINT(1) DEFAULT 0,
  country_specific VARCHAR(50), created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
DELETE FROM b11_huck_ge_probes;
INSERT INTO b11_huck_ge_probes (server_private_ip, isp_expected, city, public_ip, isp, hostname, country) VALUES
 ('192.0.2.11','CT','Shanghai (demo)','198.51.100.11','CT','demo-ct-11','China'),
 ('192.0.2.14','CT','Beijing (demo)','198.51.100.14','CT','demo-ct-14','China'),
 ('192.0.2.15','CT','Chengdu (demo)','198.51.100.15','CT','demo-ct-15','China'),
 ('192.0.2.12','CU','Beijing (demo)','198.51.100.12','CU','demo-cu-12','China'),
 ('192.0.2.16','CU','Tianjin (demo)','198.51.100.16','CU','demo-cu-16','China'),
 ('192.0.2.13','CM','Guangzhou (demo)','198.51.100.13','CM','demo-cm-13','China'),
 ('192.0.2.17','CM','Hangzhou (demo)','198.51.100.17','CM','demo-cm-17','China'),
 ('192.0.2.21','VN','Hanoi (demo)','198.51.100.21','VN','demo-vn-21','Vietnam'),
 ('192.0.2.22','VN','Ho Chi Minh City (demo)','198.51.100.22','VN','demo-vn-22','Vietnam'),
 ('192.0.2.41','INDO','Jakarta (demo)','198.51.100.41','INDO','demo-indo-41','Indonesia'),
 ('192.0.2.42','INDO','Surabaya (demo)','198.51.100.42','INDO','demo-indo-42','Indonesia'),
 ('192.0.2.51','Malaysia','Kuala Lumpur (demo)','198.51.100.51','Malaysia','demo-malaysia-51','Malaysia'),
 ('192.0.2.52','Malaysia','Penang (demo)','198.51.100.52','Malaysia','demo-malaysia-52','Malaysia'),
 ('192.0.2.61','Cambodia','Phnom Penh (demo)','198.51.100.61','Cambodia','demo-cambodia-61','Cambodia'),
 ('192.0.2.62','Cambodia','Siem Reap (demo)','198.51.100.62','Cambodia','demo-cambodia-62','Cambodia'),
 ('192.0.2.31','TH','Bangkok (demo)','198.51.100.31','TH','demo-th-31','Thailand'),
 ('192.0.2.32','TH','Chiang Mai (demo)','198.51.100.32','TH','demo-th-32','Thailand'),
 ('192.0.2.71','KR','Seoul (demo)','198.51.100.71','KR','demo-kr-71','South Korea'),
 ('192.0.2.72','KR','Busan (demo)','198.51.100.72','KR','demo-kr-72','South Korea'),
 ('192.0.2.99','CT','Offline probe (demo)','198.51.100.99','CT','demo-offline','China');
DELETE FROM c10_for_paping_probes;
INSERT INTO c10_for_paping_probes (server_ip, which_isp, which_city) VALUES
 ('192.0.2.11','CT','Shanghai (demo)'),
 ('192.0.2.14','CT','Beijing (demo)'),
 ('192.0.2.15','CT','Chengdu (demo)'),
 ('192.0.2.12','CU','Beijing (demo)'),
 ('192.0.2.16','CU','Tianjin (demo)'),
 ('192.0.2.13','CM','Guangzhou (demo)'),
 ('192.0.2.17','CM','Hangzhou (demo)'),
 ('192.0.2.21','VN','Hanoi (demo)'),
 ('192.0.2.22','VN','Ho Chi Minh City (demo)'),
 ('192.0.2.41','INDO','Jakarta (demo)'),
 ('192.0.2.42','INDO','Surabaya (demo)'),
 ('192.0.2.51','Malaysia','Kuala Lumpur (demo)'),
 ('192.0.2.52','Malaysia','Penang (demo)'),
 ('192.0.2.61','Cambodia','Phnom Penh (demo)'),
 ('192.0.2.62','Cambodia','Siem Reap (demo)'),
 ('192.0.2.31','TH','Bangkok (demo)'),
 ('192.0.2.32','TH','Chiang Mai (demo)'),
 ('192.0.2.71','KR','Seoul (demo)'),
 ('192.0.2.72','KR','Busan (demo)');
DELETE FROM a97_whitelist_conditions;
INSERT INTO a97_whitelist_conditions (condition_type, condition_pattern, condition_name, description, is_enabled, is_built_in, country_specific) VALUES
 ('success','HTTP/[0-9.]+ 200','HTTP 200','Response status 200 means OK',1,1,NULL),
 ('failure','HTTP/[0-9.]+ 5[0-9]{2}','HTTP 5xx','Any 5xx means the origin failed',1,1,NULL),
 ('failure','Connection timed out','Timeout','curl timed out',1,1,NULL);
