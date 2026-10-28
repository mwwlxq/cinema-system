select m.title, s."date", s."time", t.row_number, t.seat_number, t.price
from ticket t
join "session" s on s.id_session = t.id_session
join movie m on m.id_movie = s.id_movie
where t.is_sold = false and t.price between %s and %s
order by t.price, s."date", s."time", t.row_number, t.seat_number
limit 200
