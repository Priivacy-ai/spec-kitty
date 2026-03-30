# PlantUML Theme: Common

Minimal shared conventions for consistent, readable diagrams. Provides
foundational macros and a neutral visual baseline without imposing a strong
color scheme.

## Snippet

```plantuml
@startuml
/' Creates a colorized sprite
Params:
    e_color:    the color for the sprite
    e_sprite:   the sprite for the image '/
!define PUML_SPRITE(e_color,e_sprite) <color:e_color><$e_sprite></color>

/' Creates an aliased entity with a colorized sprite and stereotype
Params:
    e_type:     the entity type (e.g. component, node, agent, etc.)
    e_color:    the color for the sprite
    e_sprite:   the sprite for the image representing the entity
    e_alias:    the alias to give the entity
    e_stereo:   the stereotype, which can define additional styling '/
!define PUML_ENTITY(e_type,e_color,e_sprite,e_alias,e_stereo) e_type "<color:e_color><$e_sprite></color>" as e_alias <<e_stereo>>

/' Creates an aliased entity with a colorized sprite, label, and stereotype
Params:
    e_type:     the entity type (e.g. component, node, agent, etc.)
    e_color:    the color for the sprite
    e_sprite:   the sprite for the image representing the entity
    e_label:    the label to display under the sprite
    e_alias:    the alias to give the entity
    e_stereo:   the stereotype, which can define additional styling '/
!define PUML_ENTITY(e_type,e_color,e_sprite,e_label,e_alias,e_stereo) e_type "<color:e_color><$e_sprite></color>\r e_label" as e_alias <<e_stereo>>

skinparam defaultTextAlignment center

' Your diagram content here

@enduml
```

## Recommended Use

1. Neutral ADR and technical design diagrams.
2. Teaching or exploring PlantUML basics without visual opinion.
3. Maximum portability across contexts where custom colors/fonts may not
   render consistently.
