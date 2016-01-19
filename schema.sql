drop table if exists validation_results;
create table validation_results (
  uuid text primary key,
  date text not null,
  validation text not null,
  status text not null,
  detailed_description text,
  plan_id text,
  arguments text
);
