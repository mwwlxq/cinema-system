select title, hall_name, "time"
from cinema_schedule
where "date" = %s
order by "time"
