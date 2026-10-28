-- Таблица внутренних пользователей ИС «Кинотеатр» (выполнить один раз в DBeaver)
create table if not exists internal_user (
    user_id    serial primary key,
    login      varchar(50)  not null unique,
    password   varchar(100) not null,
    user_group varchar(20)  not null check (user_group in ('admin', 'manager', 'cashier'))
);

insert into internal_user (login, password, user_group) values
    ('admin',   'admin',   'admin'),
    ('manager', 'manager', 'manager'),
    ('cashier', 'cashier', 'cashier')
on conflict (login) do nothing;
