-- =====================================================
-- 汽车分期智能管理平台数据库设计
-- 项目名称：基于多模态AI的汽车分期智能管理平台
-- 版本：V1.0
-- 日期：2026-04-02
-- 数据库：MySQL 8.0
-- =====================================================

-- 设置字符集
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- =====================================================
-- 1. 用户权限模块
-- =====================================================

-- 1.1 角色表
DROP TABLE IF EXISTS `sys_role`;
CREATE TABLE `sys_role` (
  `role_id` INT NOT NULL AUTO_INCREMENT COMMENT '角色ID',
  `role_name` VARCHAR(50) NOT NULL COMMENT '角色名称',
  `role_code` VARCHAR(50) NOT NULL COMMENT '角色代码',
  `description` VARCHAR(200) DEFAULT NULL COMMENT '角色描述',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '状态：1-启用 0-禁用',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`role_id`),
  UNIQUE KEY `uk_role_code` (`role_code`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色表';

-- 1.2 部门表
DROP TABLE IF EXISTS `sys_department`;
CREATE TABLE `sys_department` (
  `dept_id` INT NOT NULL AUTO_INCREMENT COMMENT '部门ID',
  `dept_name` VARCHAR(100) NOT NULL COMMENT '部门名称',
  `parent_id` INT DEFAULT 0 COMMENT '父部门ID',
  `sort` INT DEFAULT 0 COMMENT '排序',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '状态：1-启用 0-禁用',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`dept_id`),
  KEY `idx_parent_id` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='部门表';

-- 1.3 系统用户表
DROP TABLE IF EXISTS `sys_user`;
CREATE TABLE `sys_user` (
  `user_id` INT NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username` VARCHAR(50) NOT NULL COMMENT '账号',
  `password` VARCHAR(255) NOT NULL COMMENT '密码（加密）',
  `real_name` VARCHAR(50) NOT NULL COMMENT '姓名',
  `phone` VARCHAR(20) DEFAULT NULL COMMENT '手机号',
  `email` VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
  `dept_id` INT DEFAULT NULL COMMENT '部门ID',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '状态：1-启用 0-禁用',
  `last_login_time` DATETIME DEFAULT NULL COMMENT '最后登录时间',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `uk_username` (`username`),
  KEY `idx_dept_id` (`dept_id`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_user_dept` FOREIGN KEY (`dept_id`) REFERENCES `sys_department` (`dept_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统用户表';

-- 1.4 用户角色关联表
DROP TABLE IF EXISTS `sys_user_role`;
CREATE TABLE `sys_user_role` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `user_id` INT NOT NULL COMMENT '用户ID',
  `role_id` INT NOT NULL COMMENT '角色ID',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_role` (`user_id`, `role_id`),
  KEY `idx_role_id` (`role_id`),
  CONSTRAINT `fk_ur_user` FOREIGN KEY (`user_id`) REFERENCES `sys_user` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ur_role` FOREIGN KEY (`role_id`) REFERENCES `sys_role` (`role_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户角色关联表';

-- =====================================================
-- 2. 客户与车辆管理模块
-- =====================================================

-- 2.1 客户信息表
DROP TABLE IF EXISTS `customer`;
CREATE TABLE `customer` (
  `customer_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '客户ID',
  `name` VARCHAR(50) NOT NULL COMMENT '姓名',
  `phone` VARCHAR(20) NOT NULL COMMENT '手机号',
  `id_card` VARCHAR(18) NOT NULL COMMENT '身份证号',
  `gender` TINYINT DEFAULT NULL COMMENT '性别：1-男 2-女',
  `birthday` DATE DEFAULT NULL COMMENT '出生日期',
  `province` VARCHAR(50) DEFAULT NULL COMMENT '省份',
  `city` VARCHAR(50) DEFAULT NULL COMMENT '城市',
  `district` VARCHAR(50) DEFAULT NULL COMMENT '区县',
  `address` VARCHAR(255) DEFAULT NULL COMMENT '详细地址',
  `emergency_contact` VARCHAR(50) DEFAULT NULL COMMENT '紧急联系人',
  `emergency_phone` VARCHAR(20) DEFAULT NULL COMMENT '紧急联系电话',
  `credit_score` INT DEFAULT NULL COMMENT '信用评分',
  `remark` TEXT DEFAULT NULL COMMENT '备注',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`customer_id`),
  UNIQUE KEY `uk_id_card` (`id_card`),
  KEY `idx_phone` (`phone`),
  KEY `idx_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='客户信息表';

-- 2.2 车辆信息表
DROP TABLE IF EXISTS `vehicle`;
CREATE TABLE `vehicle` (
  `vehicle_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '车辆ID',
  `vin` VARCHAR(17) NOT NULL COMMENT '车架号（VIN）',
  `plate_number` VARCHAR(20) DEFAULT NULL COMMENT '车牌号',
  `brand` VARCHAR(50) NOT NULL COMMENT '品牌',
  `model` VARCHAR(100) NOT NULL COMMENT '车型',
  `color` VARCHAR(20) DEFAULT NULL COMMENT '颜色',
  `engine_no` VARCHAR(50) DEFAULT NULL COMMENT '发动机号',
  `registration_date` DATE DEFAULT NULL COMMENT '上牌日期',
  `vehicle_price` DECIMAL(12,2) NOT NULL COMMENT '车辆价格',
  `certificate_no` VARCHAR(100) DEFAULT NULL COMMENT '登记证编号',
  `vehicle_status` TINYINT NOT NULL DEFAULT 1 COMMENT '车辆状态：1-在库 2-已售 3-抵押中',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`vehicle_id`),
  UNIQUE KEY `uk_vin` (`vin`),
  KEY `idx_plate_number` (`plate_number`),
  KEY `idx_brand` (`brand`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='车辆信息表';

-- =====================================================
-- 3. 订单管理模块
-- =====================================================

-- 3.1 订单主表
DROP TABLE IF EXISTS `orders`;
CREATE TABLE `orders` (
  `order_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '订单ID',
  `order_no` VARCHAR(50) NOT NULL COMMENT '订单号',
  `customer_id` BIGINT NOT NULL COMMENT '客户ID',
  `vehicle_id` BIGINT NOT NULL COMMENT '车辆ID',
  `sales_user_id` INT NOT NULL COMMENT '接单员工ID',
  
  -- 贷款信息
  `down_payment` DECIMAL(12,2) NOT NULL COMMENT '首付金额',
  `loan_amount` DECIMAL(12,2) NOT NULL COMMENT '贷款金额',
  `loan_term` INT NOT NULL COMMENT '贷款期数',
  `monthly_payment` DECIMAL(10,2) NOT NULL COMMENT '月供金额',
  `interest_rate` DECIMAL(5,4) DEFAULT NULL COMMENT '利率',
  
  -- 订单状态
  `order_status` TINYINT NOT NULL DEFAULT 1 COMMENT '订单状态：1-待审核 2-审核通过 3-审核拒绝 4-放款中 5-已放款 6-已结清 7-已取消',
  `order_source` VARCHAR(50) DEFAULT NULL COMMENT '订单来源',
  
  -- 时间节点
  `submit_time` DATETIME DEFAULT NULL COMMENT '提交时间',
  `approve_time` DATETIME DEFAULT NULL COMMENT '审批时间',
  `loan_time` DATETIME DEFAULT NULL COMMENT '放款时间',
  `settle_time` DATETIME DEFAULT NULL COMMENT '结清时间',
  
  `remark` TEXT DEFAULT NULL COMMENT '备注',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`order_id`),
  UNIQUE KEY `uk_order_no` (`order_no`),
  KEY `idx_customer_id` (`customer_id`),
  KEY `idx_vehicle_id` (`vehicle_id`),
  KEY `idx_sales_user_id` (`sales_user_id`),
  KEY `idx_order_status` (`order_status`),
  KEY `idx_create_time` (`create_time`),
  CONSTRAINT `fk_order_customer` FOREIGN KEY (`customer_id`) REFERENCES `customer` (`customer_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_order_vehicle` FOREIGN KEY (`vehicle_id`) REFERENCES `vehicle` (`vehicle_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_order_user` FOREIGN KEY (`sales_user_id`) REFERENCES `sys_user` (`user_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订单主表';

-- =====================================================
-- 4. 垫资管理模块（核心）
-- =====================================================

-- 4.1 垫资单表
DROP TABLE IF EXISTS `advance_payment`;
CREATE TABLE `advance_payment` (
  `advance_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '垫资ID',
  `advance_no` VARCHAR(50) NOT NULL COMMENT '垫资单号',
  `order_id` BIGINT NOT NULL COMMENT '关联订单ID',
  
  -- 垫资信息
  `advance_amount` DECIMAL(12,2) NOT NULL COMMENT '垫资金额',
  `advance_type` TINYINT NOT NULL COMMENT '垫资方类型：1-公司垫资 2-第三方垫资 3-银行垫资',
  `advance_account` VARCHAR(100) DEFAULT NULL COMMENT '垫资账户',
  `advance_bank` VARCHAR(100) DEFAULT NULL COMMENT '垫资银行/机构',
  
  -- 利息信息
  `interest_rate` DECIMAL(5,4) NOT NULL COMMENT '利率',
  `interest_type` TINYINT NOT NULL COMMENT '计息方式：1-按日计息 2-按月计息 3-固定利息',
  `interest_amount` DECIMAL(12,2) DEFAULT 0.00 COMMENT '利息金额',
  
  -- 日期信息
  `start_date` DATE NOT NULL COMMENT '垫资开始日期',
  `end_date` DATE DEFAULT NULL COMMENT '垫资结束日期',
  `actual_end_date` DATE DEFAULT NULL COMMENT '实际还款日期',
  
  -- 还款信息
  `repaid_amount` DECIMAL(12,2) DEFAULT 0.00 COMMENT '实还金额',
  `repaid_interest` DECIMAL(12,2) DEFAULT 0.00 COMMENT '实还利息',
  
  -- 状态
  `advance_status` TINYINT NOT NULL DEFAULT 1 COMMENT '状态：1-待审批 2-审批通过 3-审批拒绝 4-已出账 5-已还清 6-逾期',
  
  -- 时间节点
  `apply_time` DATETIME NOT NULL COMMENT '申请时间',
  `approve_time` DATETIME DEFAULT NULL COMMENT '审批时间',
  `disburse_time` DATETIME DEFAULT NULL COMMENT '出账时间',
  `settle_time` DATETIME DEFAULT NULL COMMENT '结清时间',
  
  `remark` TEXT DEFAULT NULL COMMENT '备注',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`advance_id`),
  UNIQUE KEY `uk_advance_no` (`advance_no`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_advance_status` (`advance_status`),
  KEY `idx_start_date` (`start_date`),
  KEY `idx_advance_type` (`advance_type`),
  CONSTRAINT `fk_advance_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`order_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='垫资单表';

-- 4.2 垫资审批记录表
DROP TABLE IF EXISTS `advance_payment_approval`;
CREATE TABLE `advance_payment_approval` (
  `approval_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '审批ID',
  `advance_id` BIGINT NOT NULL COMMENT '垫资ID',
  `approver_id` INT NOT NULL COMMENT '审批人ID',
  `approval_status` TINYINT NOT NULL COMMENT '审批状态：1-通过 2-拒绝',
  `approval_opinion` TEXT DEFAULT NULL COMMENT '审批意见',
  `approval_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '审批时间',
  
  PRIMARY KEY (`approval_id`),
  KEY `idx_advance_id` (`advance_id`),
  KEY `idx_approver_id` (`approver_id`),
  KEY `idx_approval_time` (`approval_time`),
  CONSTRAINT `fk_approval_advance` FOREIGN KEY (`advance_id`) REFERENCES `advance_payment` (`advance_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_approval_user` FOREIGN KEY (`approver_id`) REFERENCES `sys_user` (`user_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='垫资审批记录表';

-- 4.3 垫资还款记录表
DROP TABLE IF EXISTS `advance_payment_repayment`;
CREATE TABLE `advance_payment_repayment` (
  `repayment_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '还款ID',
  `advance_id` BIGINT NOT NULL COMMENT '垫资ID',
  `repayment_amount` DECIMAL(12,2) NOT NULL COMMENT '还款金额',
  `repayment_interest` DECIMAL(12,2) DEFAULT 0.00 COMMENT '还款利息',
  `repayment_principal` DECIMAL(12,2) NOT NULL COMMENT '还款本金',
  `repayment_method` TINYINT NOT NULL COMMENT '还款方式：1-银行转账 2-现金 3-微信 4-支付宝',
  `repayment_account` VARCHAR(100) DEFAULT NULL COMMENT '还款账户',
  `repayment_time` DATETIME NOT NULL COMMENT '还款时间',
  `operator_id` INT DEFAULT NULL COMMENT '操作人ID',
  `voucher_url` VARCHAR(255) DEFAULT NULL COMMENT '凭证URL',
  `remark` TEXT DEFAULT NULL COMMENT '备注',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  
  PRIMARY KEY (`repayment_id`),
  KEY `idx_advance_id` (`advance_id`),
  KEY `idx_repayment_time` (`repayment_time`),
  KEY `idx_operator_id` (`operator_id`),
  CONSTRAINT `fk_repayment_advance` FOREIGN KEY (`advance_id`) REFERENCES `advance_payment` (`advance_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_repayment_operator` FOREIGN KEY (`operator_id`) REFERENCES `sys_user` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='垫资还款记录表';

-- =====================================================
-- 5. GPS管理模块
-- =====================================================

-- 5.1 GPS设备表
DROP TABLE IF EXISTS `gps_device`;
CREATE TABLE `gps_device` (
  `device_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '设备ID',
  `device_no` VARCHAR(50) NOT NULL COMMENT '设备编号',
  `imei` VARCHAR(50) NOT NULL COMMENT 'IMEI号',
  `device_type` VARCHAR(50) NOT NULL COMMENT '设备类型',
  `order_id` BIGINT DEFAULT NULL COMMENT '关联订单ID',
  `vin` VARCHAR(17) DEFAULT NULL COMMENT '车架号',
  `install_location` VARCHAR(100) DEFAULT NULL COMMENT '安装位置',
  `install_photos` JSON DEFAULT NULL COMMENT '安装照片URL数组',
  `installer_id` INT DEFAULT NULL COMMENT '安装人员ID',
  `install_date` DATE DEFAULT NULL COMMENT '安装日期',
  `online_status` TINYINT NOT NULL DEFAULT 0 COMMENT '在线状态：1-在线 0-离线',
  `last_heartbeat_time` DATETIME DEFAULT NULL COMMENT '最后心跳时间',
  `current_longitude` DECIMAL(10,6) DEFAULT NULL COMMENT '当前经度',
  `current_latitude` DECIMAL(10,6) DEFAULT NULL COMMENT '当前纬度',
  `device_status` TINYINT NOT NULL DEFAULT 1 COMMENT '设备状态：1-正常 2-故障 3-已拆除',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`device_id`),
  UNIQUE KEY `uk_device_no` (`device_no`),
  UNIQUE KEY `uk_imei` (`imei`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_vin` (`vin`),
  KEY `idx_online_status` (`online_status`),
  KEY `idx_install_date` (`install_date`),
  CONSTRAINT `fk_gps_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`order_id`) ON DELETE SET NULL,
  CONSTRAINT `fk_gps_installer` FOREIGN KEY (`installer_id`) REFERENCES `sys_user` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='GPS设备表';

-- 5.2 GPS告警记录表
DROP TABLE IF EXISTS `gps_alarm`;
CREATE TABLE `gps_alarm` (
  `alarm_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '告警ID',
  `device_id` BIGINT NOT NULL COMMENT '设备ID',
  `order_id` BIGINT DEFAULT NULL COMMENT '关联订单ID',
  `alarm_type` VARCHAR(50) NOT NULL COMMENT '告警类型：断电告警/越界告警/低电量告警/设备拆除/异常移动',
  `alarm_level` TINYINT NOT NULL DEFAULT 1 COMMENT '告警级别：1-一般 2-重要 3-紧急',
  `alarm_time` DATETIME NOT NULL COMMENT '告警时间',
  `alarm_longitude` DECIMAL(10,6) DEFAULT NULL COMMENT '告警经度',
  `alarm_latitude` DECIMAL(10,6) DEFAULT NULL COMMENT '告警纬度',
  `alarm_address` VARCHAR(255) DEFAULT NULL COMMENT '告警地址',
  `handle_status` TINYINT NOT NULL DEFAULT 1 COMMENT '处理状态：1-待处理 2-处理中 3-已处理 4-已忽略',
  `handler_id` INT DEFAULT NULL COMMENT '处理人ID',
  `handle_time` DATETIME DEFAULT NULL COMMENT '处理时间',
  `handle_result` TEXT DEFAULT NULL COMMENT '处理结果',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`alarm_id`),
  KEY `idx_device_id` (`device_id`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_alarm_type` (`alarm_type`),
  KEY `idx_alarm_time` (`alarm_time`),
  KEY `idx_handle_status` (`handle_status`),
  CONSTRAINT `fk_alarm_device` FOREIGN KEY (`device_id`) REFERENCES `gps_device` (`device_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_alarm_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`order_id`) ON DELETE SET NULL,
  CONSTRAINT `fk_alarm_handler` FOREIGN KEY (`handler_id`) REFERENCES `sys_user` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='GPS告警记录表';

-- =====================================================
-- 6. 资料归档模块
-- =====================================================

-- 6.1 归档资料表
DROP TABLE IF EXISTS `document`;
CREATE TABLE `document` (
  `document_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '资料ID',
  `order_id` BIGINT NOT NULL COMMENT '关联订单ID',
  `document_type` VARCHAR(50) NOT NULL COMMENT '资料类型：身份证/驾驶证/行驶证/登记证/保险单/购车发票/合同等',
  `document_name` VARCHAR(100) NOT NULL COMMENT '资料名称',
  `file_url` VARCHAR(500) NOT NULL COMMENT '文件URL',
  `file_type` VARCHAR(20) DEFAULT NULL COMMENT '文件类型：jpg/png/pdf等',
  `file_size` BIGINT DEFAULT NULL COMMENT '文件大小（字节）',
  `ocr_result` JSON DEFAULT NULL COMMENT 'OCR识别结果（JSON格式）',
  `uploader_id` INT NOT NULL COMMENT '上传人员ID',
  `upload_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  `verify_status` TINYINT DEFAULT 0 COMMENT '验证状态：0-未验证 1-验证通过 2-验证失败',
  `verify_time` DATETIME DEFAULT NULL COMMENT '验证时间',
  `verify_user_id` INT DEFAULT NULL COMMENT '验证人ID',
  `remark` TEXT DEFAULT NULL COMMENT '备注',
  
  PRIMARY KEY (`document_id`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_document_type` (`document_type`),
  KEY `idx_upload_time` (`upload_time`),
  KEY `idx_uploader_id` (`uploader_id`),
  CONSTRAINT `fk_document_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`order_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_document_uploader` FOREIGN KEY (`uploader_id`) REFERENCES `sys_user` (`user_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_document_verify_user` FOREIGN KEY (`verify_user_id`) REFERENCES `sys_user` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='归档资料表';

-- 6.2 归档清单表
DROP TABLE IF EXISTS `document_checklist`;
CREATE TABLE `document_checklist` (
  `checklist_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '清单ID',
  `order_id` BIGINT NOT NULL COMMENT '关联订单ID',
  `document_type` VARCHAR(50) NOT NULL COMMENT '所需资料类型',
  `document_name` VARCHAR(100) NOT NULL COMMENT '资料名称',
  `is_required` TINYINT NOT NULL DEFAULT 1 COMMENT '是否必须：1-必须 0-可选',
  `check_status` TINYINT NOT NULL DEFAULT 0 COMMENT '状态：0-未上传 1-已上传 2-已审核',
  `document_id` BIGINT DEFAULT NULL COMMENT '关联资料ID',
  `check_time` DATETIME DEFAULT NULL COMMENT '审核时间',
  `check_user_id` INT DEFAULT NULL COMMENT '审核人ID',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`checklist_id`),
  UNIQUE KEY `uk_order_document_type` (`order_id`, `document_type`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_check_status` (`check_status`),
  CONSTRAINT `fk_checklist_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`order_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_checklist_document` FOREIGN KEY (`document_id`) REFERENCES `document` (`document_id`) ON DELETE SET NULL,
  CONSTRAINT `fk_checklist_check_user` FOREIGN KEY (`check_user_id`) REFERENCES `sys_user` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='归档清单表';

-- =====================================================
-- 7. 抵押管理模块
-- =====================================================

-- 7.1 抵押登记表
DROP TABLE IF EXISTS `mortgage`;
CREATE TABLE `mortgage` (
  `mortgage_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '登记ID',
  `order_id` BIGINT NOT NULL COMMENT '关联订单ID',
  `vin` VARCHAR(17) NOT NULL COMMENT '车架号',
  `plate_number` VARCHAR(20) DEFAULT NULL COMMENT '车牌号',
  `certificate_no` VARCHAR(100) NOT NULL COMMENT '登记证编号',
  `mortgage_bank` VARCHAR(100) NOT NULL COMMENT '抵押银行',
  `mortgage_amount` DECIMAL(12,2) DEFAULT NULL COMMENT '抵押金额',
  `registration_date` DATE NOT NULL COMMENT '登记日期',
  `expiry_date` DATE DEFAULT NULL COMMENT '到期日期',
  `release_date` DATE DEFAULT NULL COMMENT '解押日期',
  `mortgage_status` TINYINT NOT NULL DEFAULT 1 COMMENT '状态：1-抵押中 2-已解押 3-已过期',
  `operator_id` INT DEFAULT NULL COMMENT '操作人ID',
  `remark` TEXT DEFAULT NULL COMMENT '备注',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`mortgage_id`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_vin` (`vin`),
  KEY `idx_plate_number` (`plate_number`),
  KEY `idx_mortgage_status` (`mortgage_status`),
  KEY `idx_registration_date` (`registration_date`),
  CONSTRAINT `fk_mortgage_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`order_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_mortgage_operator` FOREIGN KEY (`operator_id`) REFERENCES `sys_user` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='抵押登记表';

-- =====================================================
-- 8. 还款管理模块
-- =====================================================

-- 8.1 还款计划表
DROP TABLE IF EXISTS `repayment_plan`;
CREATE TABLE `repayment_plan` (
  `plan_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '计划ID',
  `order_id` BIGINT NOT NULL COMMENT '关联订单ID',
  `period_number` INT NOT NULL COMMENT '期数',
  `plan_date` DATE NOT NULL COMMENT '应还日期',
  `plan_amount` DECIMAL(10,2) NOT NULL COMMENT '应还金额',
  `plan_principal` DECIMAL(10,2) DEFAULT NULL COMMENT '应还本金',
  `plan_interest` DECIMAL(10,2) DEFAULT NULL COMMENT '应还利息',
  `repayment_status` TINYINT NOT NULL DEFAULT 1 COMMENT '状态：1-待还款 2-已还款 3-逾期 4-部分还款',
  `actual_date` DATE DEFAULT NULL COMMENT '实还日期',
  `actual_amount` DECIMAL(10,2) DEFAULT 0.00 COMMENT '实还金额',
  `overdue_days` INT DEFAULT 0 COMMENT '逾期天数',
  `penalty_amount` DECIMAL(10,2) DEFAULT 0.00 COMMENT '违约金',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`plan_id`),
  UNIQUE KEY `uk_order_period` (`order_id`, `period_number`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_plan_date` (`plan_date`),
  KEY `idx_repayment_status` (`repayment_status`),
  CONSTRAINT `fk_plan_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`order_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='还款计划表';

-- 8.2 还款记录表
DROP TABLE IF EXISTS `repayment_record`;
CREATE TABLE `repayment_record` (
  `record_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `plan_id` BIGINT NOT NULL COMMENT '还款计划ID',
  `order_id` BIGINT NOT NULL COMMENT '关联订单ID',
  `repayment_amount` DECIMAL(10,2) NOT NULL COMMENT '实还金额',
  `repayment_principal` DECIMAL(10,2) DEFAULT NULL COMMENT '还款本金',
  `repayment_interest` DECIMAL(10,2) DEFAULT NULL COMMENT '还款利息',
  `repayment_penalty` DECIMAL(10,2) DEFAULT 0.00 COMMENT '还款违约金',
  `payment_method` TINYINT NOT NULL COMMENT '支付方式：1-银行转账 2-微信 3-支付宝 4-现金 5-代扣',
  `payment_account` VARCHAR(100) DEFAULT NULL COMMENT '支付账户',
  `transaction_no` VARCHAR(100) DEFAULT NULL COMMENT '交易流水号',
  `repayment_time` DATETIME NOT NULL COMMENT '实还时间',
  `operator_id` INT DEFAULT NULL COMMENT '操作人ID',
  `voucher_url` VARCHAR(255) DEFAULT NULL COMMENT '凭证URL',
  `remark` TEXT DEFAULT NULL COMMENT '备注',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  
  PRIMARY KEY (`record_id`),
  KEY `idx_plan_id` (`plan_id`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_repayment_time` (`repayment_time`),
  KEY `idx_transaction_no` (`transaction_no`),
  CONSTRAINT `fk_record_plan` FOREIGN KEY (`plan_id`) REFERENCES `repayment_plan` (`plan_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_record_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`order_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_record_operator` FOREIGN KEY (`operator_id`) REFERENCES `sys_user` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='还款记录表';

-- =====================================================
-- 9. 通知记录模块
-- =====================================================

-- 9.1 通知日志表
DROP TABLE IF EXISTS `notification_log`;
CREATE TABLE `notification_log` (
  `notification_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '通知ID',
  `order_id` BIGINT DEFAULT NULL COMMENT '关联订单ID',
  `notification_type` VARCHAR(50) NOT NULL COMMENT '通知类型：还款提醒/逾期提醒/审批通知/GPS告警/系统通知等',
  `notification_channel` TINYINT NOT NULL COMMENT '发送渠道：1-短信 2-微信 3-邮件 4-APP推送 5-电话',
  `recipient` VARCHAR(100) NOT NULL COMMENT '接收人（手机号/邮箱/用户ID）',
  `recipient_name` VARCHAR(50) DEFAULT NULL COMMENT '接收人姓名',
  `content` TEXT NOT NULL COMMENT '通知内容',
  `content_summary` VARCHAR(200) DEFAULT NULL COMMENT '内容摘要',
  `send_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '发送时间',
  `send_status` TINYINT NOT NULL DEFAULT 1 COMMENT '发送状态：1-发送中 2-发送成功 3-发送失败',
  `error_message` VARCHAR(500) DEFAULT NULL COMMENT '错误信息',
  `retry_count` INT DEFAULT 0 COMMENT '重试次数',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  
  PRIMARY KEY (`notification_id`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_notification_type` (`notification_type`),
  KEY `idx_send_time` (`send_time`),
  KEY `idx_send_status` (`send_status`),
  KEY `idx_recipient` (`recipient`),
  CONSTRAINT `fk_notification_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`order_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='通知日志表';

-- =====================================================
-- 10. 银行审批接口模块（预留）
-- =====================================================

-- 10.1 银行接口配置表
DROP TABLE IF EXISTS `bank_api_config`;
CREATE TABLE `bank_api_config` (
  `config_id` INT NOT NULL AUTO_INCREMENT COMMENT '配置ID',
  `bank_name` VARCHAR(100) NOT NULL COMMENT '银行名称',
  `bank_code` VARCHAR(50) NOT NULL COMMENT '银行代码',
  `api_url` VARCHAR(255) NOT NULL COMMENT 'API地址',
  `api_key` VARCHAR(255) DEFAULT NULL COMMENT 'API密钥（加密存储）',
  `api_secret` VARCHAR(255) DEFAULT NULL COMMENT 'API密钥密文（加密存储）',
  `interface_type` VARCHAR(50) DEFAULT NULL COMMENT '接口类型',
  `timeout` INT DEFAULT 30000 COMMENT '超时时间（毫秒）',
  `retry_times` INT DEFAULT 3 COMMENT '重试次数',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '状态：1-启用 0-禁用',
  `remark` TEXT DEFAULT NULL COMMENT '备注',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`config_id`),
  UNIQUE KEY `uk_bank_code` (`bank_code`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='银行接口配置表';

-- 10.2 银行申请记录表
DROP TABLE IF EXISTS `bank_application`;
CREATE TABLE `bank_application` (
  `application_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '银行申请ID',
  `order_id` BIGINT NOT NULL COMMENT '关联订单ID',
  `bank_code` VARCHAR(50) NOT NULL COMMENT '银行代码',
  `bank_name` VARCHAR(100) NOT NULL COMMENT '银行名称',
  `application_no` VARCHAR(100) DEFAULT NULL COMMENT '银行申请单号',
  `apply_time` DATETIME NOT NULL COMMENT '申请时间',
  `apply_amount` DECIMAL(12,2) NOT NULL COMMENT '申请金额',
  `application_status` TINYINT NOT NULL DEFAULT 1 COMMENT '状态：1-申请中 2-审批中 3-审批通过 4-审批拒绝 5-已撤回',
  `approve_time` DATETIME DEFAULT NULL COMMENT '审批时间',
  `approve_amount` DECIMAL(12,2) DEFAULT NULL COMMENT '审批金额',
  `reject_reason` VARCHAR(500) DEFAULT NULL COMMENT '拒绝原因',
  `response_data` JSON DEFAULT NULL COMMENT '银行响应数据',
  `operator_id` INT DEFAULT NULL COMMENT '操作人ID',
  `remark` TEXT DEFAULT NULL COMMENT '备注',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`application_id`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_bank_code` (`bank_code`),
  KEY `idx_application_status` (`application_status`),
  KEY `idx_apply_time` (`apply_time`),
  KEY `idx_application_no` (`application_no`),
  CONSTRAINT `fk_bank_app_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`order_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_bank_app_operator` FOREIGN KEY (`operator_id`) REFERENCES `sys_user` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='银行申请记录表';

-- 10.3 银行接口日志表
DROP TABLE IF EXISTS `bank_api_log`;
CREATE TABLE `bank_api_log` (
  `log_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  `application_id` BIGINT DEFAULT NULL COMMENT '银行申请ID',
  `bank_code` VARCHAR(50) NOT NULL COMMENT '银行代码',
  `api_type` VARCHAR(50) NOT NULL COMMENT '接口类型：申请/查询/撤销等',
  `request_data` JSON DEFAULT NULL COMMENT '请求数据',
  `response_data` JSON DEFAULT NULL COMMENT '响应数据',
  `request_time` DATETIME NOT NULL COMMENT '请求时间',
  `response_time` DATETIME DEFAULT NULL COMMENT '响应时间',
  `duration` INT DEFAULT NULL COMMENT '耗时（毫秒）',
  `status` TINYINT NOT NULL COMMENT '状态：1-成功 2-失败',
  `error_message` VARCHAR(500) DEFAULT NULL COMMENT '错误信息',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  
  PRIMARY KEY (`log_id`),
  KEY `idx_application_id` (`application_id`),
  KEY `idx_bank_code` (`bank_code`),
  KEY `idx_request_time` (`request_time`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='银行接口日志表';

-- =====================================================
-- 11. 系统配置模块
-- =====================================================

-- 11.1 系统配置表
DROP TABLE IF EXISTS `system_config`;
CREATE TABLE `system_config` (
  `config_id` INT NOT NULL AUTO_INCREMENT COMMENT '配置ID',
  `config_key` VARCHAR(100) NOT NULL COMMENT '配置键',
  `config_value` TEXT DEFAULT NULL COMMENT '配置值',
  `config_type` VARCHAR(50) DEFAULT 'text' COMMENT '配置类型：text/json/number/boolean',
  `config_group` VARCHAR(50) DEFAULT NULL COMMENT '配置分组',
  `description` VARCHAR(200) DEFAULT NULL COMMENT '配置说明',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`config_id`),
  UNIQUE KEY `uk_config_key` (`config_key`),
  KEY `idx_config_group` (`config_group`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';

-- 11.2 操作日志表
DROP TABLE IF EXISTS `operation_log`;
CREATE TABLE `operation_log` (
  `log_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  `user_id` INT DEFAULT NULL COMMENT '操作用户ID',
  `username` VARCHAR(50) DEFAULT NULL COMMENT '操作用户名',
  `module` VARCHAR(50) DEFAULT NULL COMMENT '模块名称',
  `operation` VARCHAR(100) DEFAULT NULL COMMENT '操作描述',
  `method` VARCHAR(200) DEFAULT NULL COMMENT '请求方法',
  `request_url` VARCHAR(255) DEFAULT NULL COMMENT '请求URL',
  `request_method` VARCHAR(10) DEFAULT NULL COMMENT '请求方式',
  `request_params` TEXT DEFAULT NULL COMMENT '请求参数',
  `response_result` TEXT DEFAULT NULL COMMENT '响应结果',
  `ip_address` VARCHAR(50) DEFAULT NULL COMMENT 'IP地址',
  `location` VARCHAR(100) DEFAULT NULL COMMENT '操作地点',
  `browser` VARCHAR(100) DEFAULT NULL COMMENT '浏览器',
  `os` VARCHAR(100) DEFAULT NULL COMMENT '操作系统',
  `status` TINYINT DEFAULT 1 COMMENT '状态：1-成功 2-失败',
  `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
  `duration` INT DEFAULT NULL COMMENT '执行时长（毫秒）',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  
  PRIMARY KEY (`log_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_module` (`module`),
  KEY `idx_create_time` (`create_time`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='操作日志表';

-- =====================================================
-- 数据库设计完成
-- =====================================================

SET FOREIGN_KEY_CHECKS = 1;

-- =====================================================
-- ER关系图说明（文字版）
-- =====================================================
/*

========================================
汽车分期管理平台 ER 关系图
========================================

【核心实体关系】

1. 用户权限模块
   sys_department (1) ----< (N) sys_user
   sys_user (M) >----< (N) sys_role (通过 sys_user_role 关联)

2. 订单核心关系
   customer (1) ----< (N) orders
   vehicle (1) ----< (N) orders
   sys_user (1) ----< (N) orders (接单员工)
   
3. 垫资管理（核心）
   orders (1) ----< (N) advance_payment
   advance_payment (1) ----< (N) advance_payment_approval
   advance_payment (1) ----< (N) advance_payment_repayment
   sys_user (1) ----< (N) advance_payment_approval (审批人)
   
4. GPS管理
   orders (1) ----< (N) gps_device (可选关联)
   gps_device (1) ----< (N) gps_alarm
   sys_user (1) ----< (N) gps_device (安装人员)
   
5. 资料归档
   orders (1) ----< (N) document
   orders (1) ----< (N) document_checklist
   document (1) ----< (0或1) document_checklist
   
6. 抵押管理
   orders (1) ----< (N) mortgage
   vehicle (1) ----< (N) mortgage (通过VIN关联)
   
7. 还款管理
   orders (1) ----< (N) repayment_plan
   repayment_plan (1) ----< (N) repayment_record
   
8. 通知记录
   orders (1) ----< (N) notification_log
   
9. 银行审批
   orders (1) ----< (N) bank_application
   bank_api_config (1) ----< (N) bank_application (通过bank_code关联)

========================================
【主要外键关系图】

sys_department.dept_id <---- sys_user.dept_id
sys_user.user_id <---- sys_user_role.user_id
sys_role.role_id <---- sys_user_role.role_id

customer.customer_id <---- orders.customer_id
vehicle.vehicle_id <---- orders.vehicle_id
sys_user.user_id <---- orders.sales_user_id

orders.order_id <---- advance_payment.order_id
advance_payment.advance_id <---- advance_payment_approval.advance_id
advance_payment.advance_id <---- advance_payment_re   
6. 抵押管理
   orders (1) ----< (N) mortgage
   vehicle (1) ----< (N) mortgage (通过VIN关联)
   
7. 还款管理
   orders (1) ----< (N) repayment_plan
   repayment_plan (1) ----< (N) repayment_record
   
8. 通知记录
   orders (1) ----< (N) notification_log
   
9. 银行审批
   orders (1) ----< (N) bank_application
   bank_api_config (1) ----< (N) bank_application (通过bank_code关联)

========================================
【主要外键关系图】

sys_department.dept_id <---- sys_user.dept_id
sys_user.user_id <---- sys_user_role.user_id
sys_role.role_id <---- sys_user_role.role_id

customer.customer_id <---- orders.customer_id
vehicle.vehicle_id <---- orders.vehicle_id
sys_user.user_id <---- orders.sales_user_id

orders.order_id <---- advance_payment.order_id
advance_payment.advance_id <---- advance_payment_approval.advance_id
advance_payment.advance_id <---- advance_payment_repayment.advance_id
sys_user.user_id <---- advance_payment_approval.approver_id

orders.order_id <---- gps_device.order_id
gps_device.device_id <---- gps_alarm.device_id
orders.order_id <---- gps_alarm.order_id
sys_user.user_id <---- gps_device.installer_id

orders.order_id <---- document.order_id
orders.order_id <---- document_checklist.order_id
document.document_id <---- document_checklist.document_id

orders.order_id <---- mortgage.order_id

orders.order_id <---- repayment_plan.order_id
repayment_plan.plan_id <---- repayment_record.plan_id
orders.order_id <---- repayment_record.order_id

orders.order_id <---- notification_log.order_id

orders.order_id <---- bank_application.order_id
bank_api_config.bank_code <---- bank_application.bank_code

========================================
【数据表统计】

总计 25 张数据表：

用户权限模块（4张）：
  - sys_role (角色表)
  - sys_department (部门表)
  - sys_user (用户表)
  - sys_user_role (用户角色关联表)

客户与车辆（2张）：
  - customer (客户信息表)
  - vehicle (车辆信息表)

订单管理（1张）：
  - orders (订单主表)

垫资管理（3张）：
  - advance_payment (垫资单表)
  - advance_payment_approval (垫资审批记录表)
  - advance_payment_repayment (垫资还款记录表)

GPS管理（2张）：
  - gps_device (GPS设备表)
  - gps_alarm (GPS告警记录表)

资料归档（2张）：
  - document (归档资料表)
  - document_checklist (归档清单表)

抵押管理（1张）：
  - mortgage (抵押登记表)

还款管理（2张）：
  - repayment_plan (还款计划表)
  - repayment_record (还款记录表)

通知记录（1张）：
  - notification_log (通知日志表)

银行审批（3张）：
  - bank_api_config (银行接口配置表)
  - bank_application (银行申请记录表)
  - bank_api_log (银行接口日志表)

系统配置（2张）：
  - system_config (系统配置表)
  - operation_log (操作日志表)

========================================
*/

-- =====================================================
-- 初始化数据 SQL
-- =====================================================

-- 插入角色数据
INSERT INTO `sys_role` (`role_name`, `role_code`, `description`, `status`) VALUES
('老板', 'boss', '公司老板，拥有所有权限', 1),
('管理员', 'admin', '系统管理员，拥有系统管理权限', 1),
('销售', 'sales', '销售人员，负责客户跟进和订单创建', 1),
('贷后', 'post_loan', '贷后管理人员，负责还款跟踪和催收', 1),
('财务', 'finance', '财务人员，负责垫资管理和账务处理', 1),
('客服', 'customer_service', '客服人员，负责客户咨询和通知', 1);

-- 插入部门数据
INSERT INTO `sys_department` (`dept_name`, `parent_id`, `sort`, `status`) VALUES
('总公司', 0, 1, 1),
('销售部', 1, 1, 1),
('贷后部', 1, 2, 1),
('财务部', 1, 3, 1),
('客服部', 1, 4, 1),
('技术部', 1, 5, 1);

-- 插入默认管理员账号 (密码: admin123，实际使用时需加密)
INSERT INTO `sys_user` (`username`, `password`, `real_name`, `dept_id`, `status`) VALUES
('admin', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iAt6Z5EH', '系统管理员', 6, 1),
('boss', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iAt6Z5EH', '老板', 1, 1);

-- 分配角色给用户
INSERT INTO `sys_user_role` (`user_id`, `role_id`) VALUES
(1, 2), -- admin -> 管理员
(2, 1); -- boss -> 老板

-- 插入银行接口配置示例数据
INSERT INTO `bank_api_config` (`bank_name`, `bank_code`, `api_url`, `interface_type`, `status`) VALUES
('中国银行', 'BOC', 'https://api.boc.cn/loan', 'REST', 1),
('工商银行', 'ICBC', 'https://api.icbc.com.cn/loan', 'REST', 1),
('建设银行', 'CCB', 'https://api.ccb.com/loan', 'REST', 1),
('农业银行', 'ABC', 'https://api.abchina.com/loan', 'REST', 0),
('招商银行', 'CMB', 'https://api.cmbchina.com/loan', 'REST', 1);

-- 插入系统配置数据
INSERT INTO `system_config` (`config_key`, `config_value`, `config_type`, `config_group`, `description`) VALUES
('system.name', '汽车分期智能管理平台', 'text', 'basic', '系统名称'),
('system.version', '1.0.0', 'text', 'basic', '系统版本'),
('loan.default.rate', '0.05', 'number', 'loan', '默认贷款利率'),
('loan.default.term', '36', 'number', 'loan', '默认贷款期数'),
('gps.alarm.interval', '300', 'number', 'gps', 'GPS告警检查间隔（秒）'),
('notification.sms.enabled', 'true', 'boolean', 'notification', '是否启用短信通知'),
('notification.email.enabled', 'true', 'boolean', 'notification', '是否启用邮件通知');

-- 插入资料类型配置
INSERT INTO `system_config` (`config_key`, `config_value`, `config_type`, `config_group`, `description`) VALUES
('document.required.types', '["身份证","驾驶证","行驶证","登记证","保险单","购车发票","合同","银行流水"]', 'json', 'document', '必需资料类型列表');

-- =====================================================
-- 索引优化建议
-- =====================================================
/*

【查询优化索引建议】

1. 订单查询优化
   - 根据客户手机号查询订单：已在 customer.phone 建立索引
   - 根据订单状态和时间范围查询：已在 orders.order_status, orders.create_time 建立索引
   - 根据车架号查询订单：已在 vehicle.vin 建立索引

2. 垫资管理优化
   - 待审批垫资单查询：advance_payment.advance_status + advance_payment.apply_time
   - 逾期垫资单查询：advance_payment.advance_status + advance_payment.end_date
   
   可根据实际查询频率添加组合索引：
   ALTER TABLE `advance_payment` ADD INDEX `idx_status_date` (`advance_status`, `start_date`);
   ALTER TABLE `advance_payment` ADD INDEX `idx_type_status` (`advance_type`, `advance_status`);

3. GPS告警优化
   - 待处理告警查询：gps_alarm.handle_status + gps_alarm.alarm_time
   
   可添加组合索引：
   ALTER TABLE `gps_alarm` ADD INDEX `idx_status_time` (`handle_status`, `alarm_time`);

4. 还款管理优化
   - 逾期还款查询：repayment_plan.repayment_status + repayment_plan.plan_date
   
   可添加组合索引：
   ALTER TABLE `repayment_plan` ADD INDEX `idx_status_date` (`repayment_status`, `plan_date`);

5. 通知日志优化
   - 按时间和状态查询通知：notification_log.send_time + notification_log.send_status
   
   可添加组合索引：
   ALTER TABLE `notification_log` ADD INDEX `idx_time_status` (`send_time`, `send_status`);

【分区表建议】

对于数据量较大的表，建议按时间进行分区：

1. operation_log (操作日志表)
   - 建议按月分区，保留最近12个月数据
   - 历史数据可归档到历史表

2. gps_alarm (GPS告警记录表)
   - 建议按月分区，保留最近6个月热数据
   
3. bank_api_log (银行接口日志表)
   - 建议按月分区，保留最近6个月数据

4. notification_log (通知日志表)
   - 建议按月分区，保留最近12个月数据

【数据库配置建议】

1. 字符集：utf8mb4 (支持emoji和特殊字符)
2. 排序规则：utf8mb4_unicode_ci (支持多语言排序)
3. 存储引擎：InnoDB (支持事务和外键)
4. 隔离级别：READ-COMMITTED (建议，避免间隙锁)

*/

-- =====================================================
-- 视图定义（可选）
-- =====================================================

-- 订单完整信息视图
DROP VIEW IF EXISTS `v_order_detail`;
CREATE VIEW `v_order_detail` AS
SELECT 
    o.order_id,
    o.order_no,
    o.order_status,
    c.name AS customer_name,
    c.phone AS customer_phone,
    c.id_card,
    v.brand,
    v.model,
    v.vin,
    v.plate_number,
    v.vehicle_price,
    o.down_payment,
    o.loan_amount,
    o.loan_term,
    o.monthly_payment,
    u.real_name AS sales_name,
    o.create_time
FROM `orders` o
LEFT JOIN `customer` c ON o.customer_id = c.customer_id
LEFT JOIN `vehicle` v ON o.vehicle_id = v.vehicle_id
LEFT JOIN `sys_user` u ON o.sales_user_id = u.user_id;

-- 垫资统计视图
DROP VIEW IF EXISTS `v_advance_summary`;
CREATE VIEW `v_advance_summary` AS
SELECT 
    DATE(ap.start_date) AS date,
    ap.advance_type,
    COUNT(*) AS total_count,
    SUM(ap.advance_amount) AS total_amount,
    SUM(ap.repaid_amount) AS repaid_amount,
    SUM(ap.advance_amount - ap.repaid_amount) AS outstanding_amount
FROM `advance_payment` ap
GROUP BY DATE(ap.start_date), ap.advance_type;

-- 还款统计视图
DROP VIEW IF EXISTS `v_repayment_summary`;
CREATE VIEW `v_repayment_summary` AS
SELECT 
    rp.order_id,
    o.order_no,
    c.name AS customer_name,
    c.phone AS customer_phone,
    COUNT(rp.plan_id) AS total_periods,
    SUM(CASE WHEN rp.repayment_status = 2 THEN 1 ELSE 0 END) AS paid_periods,
    SUM(CASE WHEN rp.repayment_status = 3 THEN 1 ELSE 0 END) AS overdue_periods,
    SUM(rp.plan_amount) AS total_amount,
    SUM(rp.actual_amount) AS paid_amount,
    SUM(rp.plan_amount - rp.actual_amount) AS outstanding_amount
FROM `repayment_plan` rp
LEFT JOIN `orders` o ON rp.order_id = o.order_id
LEFT JOIN `customer` c ON o.customer_id = c.customer_id
GROUP BY rp.order_id, o.order_no, c.name, c.phone;

-- =====================================================
-- 存储过程示例（可选）
-- =====================================================

DELIMITER //

-- 计算逾期罚息
DROP PROCEDURE IF EXISTS `sp_calculate_overdue_penalty` //
CREATE PROCEDURE `sp_calculate_overdue_penalty`(
    IN p_plan_id BIGINT,
    OUT p_penalty_amount DECIMAL(10,2)
)
BEGIN
    DECLARE v_overdue_days INT;
    DECLARE v_plan_amount DECIMAL(10,2);
    DECLARE v_penalty_rate DECIMAL(5,4) DEFAULT 0.0005; -- 日违约金率0.05%
    
    SELECT 
        DATEDIFF(CURDATE(), plan_date),
        plan_amount
    INTO v_overdue_days, v_plan_amount
    FROM `repayment_plan`
    WHERE `plan_id` = p_plan_id;
    
    IF v_overdue_days > 0 THEN
        SET p_penalty_amount = v_plan_amount * v_penalty_rate * v_overdue_days;
    ELSE
        SET p_penalty_amount = 0;
    END IF;
END //

-- 检查订单资料完整性
DROP PROCEDURE IF EXISTS `sp_check_document_completeness` //
CREATE PROCEDURE `sp_check_document_completeness`(
    IN p_order_id BIGINT,
    OUT p_is_complete BOOLEAN,
    OUT p_missing_documents TEXT
)
BEGIN
    DECLARE v_required_count INT;
    DECLARE v_uploaded_count INT;
    
    -- 获取必须资料数量
    SELECT COUNT(*) INTO v_required_count
    FROM `document_checklist`
    WHERE `order_id` = p_order_id AND `is_required` = 1;
    
    -- 获取已上传资料数量
    SELECT COUNT(*) INTO v_uploaded_count
    FROM `document_checklist`
    WHERE `order_id` = p_order_id AND `is_required` = 1 AND `check_status` >= 1;
    
    IF v_required_count = v_uploaded_count THEN
        SET p_is_complete = TRUE;
        SET p_missing_documents = '';
    ELSE
        SET p_is_complete = FALSE;
        SELECT GROUP_CONCAT(document_name SEPARATOR ', ') INTO p_missing_documents
        FROM `document_checklist`
        WHERE `order_id` = p_order_id AND `is_required` = 1 AND `check_status` = 0;
    END IF;
END //

DELIMITER ;

-- =====================================================
-- 数据库设计完成
-- =====================================================

/*
========================================
版本历史
========================================

V1.0 - 2026-04-02
- 初始版本
- 包含25张核心数据表
- 覆盖订单、垫资、GPS、资料、抵押、还款、通知、银行接口等模块
- 完整的索引和外键约束
- 包含初始化数据和视图定义

========================================
使用说明
========================================

1. 执行本SQL文件前，请确保已创建数据库：
   CREATE DATABASE car_loan_platform DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;
   USE car_loan_platform;

2. 执行本SQL文件创建表结构：
   source 【数据库设计】汽车分期管理平台数据库表结构.sql

3. 修改默认管理员密码：
   UPDATE sys_user SET password = '加密后的密码' WHERE username = 'admin';

4. 根据实际业务调整：
   - 修改系统配置参数
   - 添加部门组织结构
   - 创建用户并分配角色
   - 配置银行接口参数

========================================
*/
