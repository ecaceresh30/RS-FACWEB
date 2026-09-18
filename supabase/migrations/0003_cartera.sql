-- Facturacion (cabecera + detalle) y cartera de cuentas por cobrar, simuladas
-- para demo, emitidas por un usuario (identificado por RUC) a sus propios
-- clientes. Requiere que el RUC emisor ya exista en `usuarios` (ver
-- 0001_usuarios_conversaciones_mensajes.sql). No toca documentos/pgvector
-- (0002) ni usuarios/conversaciones/mensajes (0001).
--
-- Aplicar manualmente en el SQL editor de Supabase Studio, o via
-- `supabase db push`.

drop table if exists cartera cascade;
drop table if exists factura_detalle cascade;
drop table if exists facturas cascade;

create table facturas (
    id uuid primary key default gen_random_uuid(),
    emisor_ruc text not null references usuarios (ruc),
    numero text not null,
    tipo_comprobante text not null check (tipo_comprobante in ('factura', 'boleta')),
    cliente_nombre text not null,
    cliente_ruc text,
    moneda text not null default 'PEN',
    forma_pago text not null check (forma_pago in ('contado', 'credito')),
    fecha_emision date not null,
    fecha_vencimiento date,
    monto_total numeric(12, 2) not null,
    estado_pago text not null check (estado_pago in ('pagado', 'pendiente', 'vencido')),
    created_at timestamptz not null default now()
);

create index facturas_emisor_ruc_idx on facturas (emisor_ruc);

create table factura_detalle (
    id uuid primary key default gen_random_uuid(),
    factura_id uuid not null references facturas (id) on delete cascade,
    descripcion text not null,
    cantidad numeric(10, 2) not null,
    precio_unitario numeric(12, 2) not null,
    subtotal numeric(12, 2) not null
);

create index factura_detalle_factura_id_idx on factura_detalle (factura_id);

-- Cartera: subconjunto de `facturas` a credito (cuentas por cobrar), una fila
-- por factura a credito, con los campos propios del seguimiento de cobranza.
create table cartera (
    id uuid primary key default gen_random_uuid(),
    factura_id uuid not null unique references facturas (id) on delete cascade,
    emisor_ruc text not null references usuarios (ruc),
    monto_pendiente numeric(12, 2) not null,
    dias_vencido integer not null default 0,
    tramo_mora text not null check (tramo_mora in ('vigente', '1-30', '31-60', '61-90', '90+')),
    created_at timestamptz not null default now()
);

create index cartera_emisor_ruc_idx on cartera (emisor_ruc);

alter table facturas enable row level security;
alter table factura_detalle enable row level security;
alter table cartera enable row level security;
