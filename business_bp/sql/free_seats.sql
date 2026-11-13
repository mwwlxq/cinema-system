SELECT row_number, seat_number, price FROM ticket
WHERE id_session = %s AND is_sold = false;