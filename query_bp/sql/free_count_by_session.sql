select m.title, s."date", s."time", count(t.id_ticket) as free_count
from "session" s
join movie m on m.id_movie = s.id_movie
left join ticket t on t.id_session = s.id_session and t.is_sold = false
where s.id_session = %s
group by m.title, s."date", s."time"
