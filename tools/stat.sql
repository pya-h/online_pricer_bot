SET time_zone = 'Asia/Tehran';
SELECT 
	COUNT(*) as all_users,
	COUNT(CASE WHEN plus_end_date IS NULL THEN 1 END) as free,
    COUNT(CASE WHEN plus_end_date IS NOT NULL THEN 1 END) as plus,


    COUNT(CASE WHEN DATE(join_date)=DATE(NOW()) THEN 1 END) as all_join_today,
    COUNT(CASE WHEN DATE(join_date) BETWEEN DATE(NOW()) - INTERVAL 1 DAY AND DATE(NOW()) THEN 1 END) as all_join_yesterday,
    COUNT(CASE WHEN DATE(join_date) BETWEEN DATE(NOW()) - INTERVAL 7 DAY AND DATE(NOW()) THEN 1 END) as all_join_lastweek,
    COUNT(CASE WHEN DATE(join_date) BETWEEN DATE(NOW()) - INTERVAL 30 DAY AND DATE(NOW()) THEN 1 END) as all_join_lastmonth,

    COUNT(CASE WHEN DATE(plus_start_date)=DATE(NOW()) THEN 1 END) as plus_today,
    COUNT(CASE WHEN DATE(plus_start_date) BETWEEN DATE(NOW()) - INTERVAL 1 DAY AND DATE(NOW()) THEN 1 END) as plus_yesterday,
    COUNT(CASE WHEN DATE(plus_start_date) BETWEEN DATE(NOW()) - INTERVAL 7 DAY AND DATE(NOW()) THEN 1 END) as plus_lastweek,
    COUNT(CASE WHEN DATE(plus_start_date) BETWEEN DATE(NOW()) - INTERVAL 30 DAY AND DATE(NOW()) THEN 1 END) as plus_lastmonth,
    
    COUNT(CASE WHEN plus_end_date IS NULL AND DATE(last_interaction)=DATE(NOW()) THEN 1 END) as free_int_today,
    COUNT(CASE WHEN plus_end_date IS NULL AND DATE(last_interaction) BETWEEN DATE(NOW()) - INTERVAL 1 DAY AND DATE(NOW()) THEN 1 END) as free_int_yesterday,
    COUNT(CASE WHEN plus_end_date IS NULL AND DATE(last_interaction) BETWEEN DATE(NOW()) - INTERVAL 7 DAY AND DATE(NOW()) THEN 1 END) as free_int_lastweek,
    COUNT(CASE WHEN plus_end_date IS NULL AND DATE(last_interaction) BETWEEN DATE(NOW()) - INTERVAL 30 DAY AND DATE(NOW()) THEN 1 END) as free_int_lastmonth,
    
    COUNT(CASE WHEN plus_end_date IS NOT NULL AND DATE(last_interaction)=DATE(NOW()) THEN 1 END) as plus_int_today,
    COUNT(CASE WHEN plus_end_date IS NOT NULL AND DATE(last_interaction) BETWEEN DATE(NOW()) - INTERVAL 1 DAY AND DATE(NOW()) THEN 1 END) as plus_int_yesterday,
    COUNT(CASE WHEN plus_end_date IS NOT NULL AND DATE(last_interaction) BETWEEN DATE(NOW()) - INTERVAL 7 DAY AND DATE(NOW()) THEN 1 END) as plus_int_lastweek,
    COUNT(CASE WHEN plus_end_date IS NOT NULL AND DATE(last_interaction) BETWEEN DATE(NOW()) - INTERVAL 30 DAY AND DATE(NOW()) THEN 1 END) as plus_int_lastmonth,
    
FROM `accounts`;

SELECT 
	COUNT(*) as all_channels
FROM `channels` WHERE is_active=1;

SELECT 
	COUNT(*) as all_groups
FROM `supergroups`;