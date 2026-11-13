using Microsoft.EntityFrameworkCore;
using Orbital.Api;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddDbContext<OrbitalDb>(o => o.UseNpgsql(
    builder.Configuration.GetConnectionString("DefaultConnection")
    ?? throw new InvalidOperationException("Configure ConnectionStrings__DefaultConnection."),
    p => p.EnableRetryOnFailure(3)));
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();
var app = builder.Build();
app.UseSwagger();
app.UseSwaggerUI();
app.MapGet("/", () => Results.Redirect("/swagger"));
app.MapGet("/health", () => Results.Ok(new { status = "healthy", service = "ZelaCidade Orbital", semestre = "2026/1", rm = "558710" }));
app.MapGet("/health/ready", async (OrbitalDb db) => {
    try {
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        await db.Areas.AsNoTracking().AnyAsync(timeout.Token);
        await db.Alertas.AsNoTracking().AnyAsync(timeout.Token);
        return Results.Ok(new { status = "ready", database = "PostgreSQL", tables = 2 });
    } catch (Exception ex) {
        app.Logger.LogWarning(ex, "Banco indisponivel.");
        return Results.Problem("Banco indisponivel ou esquema ausente.", statusCode: 503);
    }
});

var areas = app.MapGroup("/api/areas").WithTags("Areas monitoradas");
areas.MapGet("/", async (OrbitalDb db) => await db.Areas.AsNoTracking().OrderBy(x => x.Id).ToListAsync());
areas.MapGet("/{id:int}", async (int id, OrbitalDb db) => await db.Areas.FindAsync(id) is {} a ? Results.Ok(a) : Results.NotFound());
areas.MapPost("/", async (AreaInput input, OrbitalDb db) => {
    if (Rules.Validate(input) is {} error) return Results.BadRequest(new { error });
    var a = new AreaMonitorada { Nome = input.Nome.Trim(), Municipio = input.Municipio.Trim(), Latitude = input.Latitude, Longitude = input.Longitude };
    db.Areas.Add(a); await db.SaveChangesAsync(); return Results.Created($"/api/areas/{a.Id}", a);
}).Produces<AreaMonitorada>(201).Produces(400);
areas.MapPut("/{id:int}", async (int id, AreaInput input, OrbitalDb db) => {
    if (Rules.Validate(input) is {} error) return Results.BadRequest(new { error });
    if (await db.Areas.FindAsync(id) is not {} a) return Results.NotFound();
    a.Nome = input.Nome.Trim(); a.Municipio = input.Municipio.Trim(); a.Latitude = input.Latitude; a.Longitude = input.Longitude;
    await db.SaveChangesAsync(); return Results.Ok(a);
}).Produces<AreaMonitorada>().Produces(400).Produces(404);
areas.MapDelete("/{id:int}", async (int id, OrbitalDb db) => {
    if (await db.Areas.FindAsync(id) is not {} a) return Results.NotFound();
    if (await db.Alertas.AnyAsync(x => x.AreaMonitoradaId == id)) return Results.Conflict(new { error = "Area possui alertas. Exclua os alertas primeiro." });
    db.Areas.Remove(a); await db.SaveChangesAsync(); return Results.NoContent();
}).Produces(204).Produces(404).Produces(409);

var alertas = app.MapGroup("/api/alertas").WithTags("Alertas orbitais");
alertas.MapGet("/", async (OrbitalDb db) => await db.Alertas.AsNoTracking().OrderBy(x => x.Id).ToListAsync());
alertas.MapGet("/{id:int}", async (int id, OrbitalDb db) => await db.Alertas.FindAsync(id) is {} a ? Results.Ok(a) : Results.NotFound());
alertas.MapPost("/", async (AlertaInput input, OrbitalDb db) => {
    if (Rules.Validate(input) is {} error) return Results.BadRequest(new { error });
    if (!await db.Areas.AnyAsync(x => x.Id == input.AreaMonitoradaId)) return Results.BadRequest(new { error = "Area inexistente." });
    var a = new Alerta { AreaMonitoradaId = input.AreaMonitoradaId, Titulo = input.Titulo.Trim(), FonteOrbital = input.FonteOrbital.Trim(), ReferenciaObservacao = input.ReferenciaObservacao.Trim(), Status = input.Status };
    db.Alertas.Add(a); await db.SaveChangesAsync(); return Results.Created($"/api/alertas/{a.Id}", a);
}).Produces<Alerta>(201).Produces(400);
alertas.MapPut("/{id:int}", async (int id, AlertaInput input, OrbitalDb db) => {
    if (Rules.Validate(input) is {} error) return Results.BadRequest(new { error });
    if (await db.Alertas.FindAsync(id) is not {} a) return Results.NotFound();
    if (!await db.Areas.AnyAsync(x => x.Id == input.AreaMonitoradaId)) return Results.BadRequest(new { error = "Area inexistente." });
    a.AreaMonitoradaId = input.AreaMonitoradaId; a.Titulo = input.Titulo.Trim(); a.FonteOrbital = input.FonteOrbital.Trim(); a.ReferenciaObservacao = input.ReferenciaObservacao.Trim(); a.Status = input.Status;
    await db.SaveChangesAsync(); return Results.Ok(a);
}).Produces<Alerta>().Produces(400).Produces(404);
alertas.MapDelete("/{id:int}", async (int id, OrbitalDb db) => {
    if (await db.Alertas.FindAsync(id) is not {} a) return Results.NotFound();
    db.Alertas.Remove(a); await db.SaveChangesAsync(); return Results.NoContent();
}).Produces(204).Produces(404);
app.Run();
public partial class Program { }
